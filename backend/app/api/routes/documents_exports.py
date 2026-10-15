from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from supabase import create_client

from app.api.deps import require_roles
from app.core.config import get_settings
from app.db.session import get_db
from app.models import AuditLog, Profile

router = APIRouter(tags=["patient documents and exports"])
STAFF_DOCUMENT_ROLES = ("administrator", "cashier", "information_officer", "doctor", "nurse")
REVIEW_ROLES = ("administrator", "cashier")
ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_BYTES = 10 * 1024 * 1024
BUCKET = "nexuscare-patient-documents"


def _storage():
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise HTTPException(status_code=503, detail="Server storage is not configured.")
    return create_client(settings.supabase_url, settings.supabase_secret_key).storage.from_(BUCKET)


def _safe_filename(name: str | None) -> str:
    raw = (name or "document").replace("\\", "/").split("/")[-1]
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", raw)[:180]
    return cleaned or "document"


@router.post("/patients/{patient_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_patient_document(
    patient_id: UUID,
    document_type: str = Form(..., pattern="^(senior_id|pwd_id|philhealth_id|insurance|other)$"),
    file: UploadFile = File(...),
    profile: Profile = Depends(require_roles(*STAFF_DOCUMENT_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    patient = db.execute(text("select id from public.patients where id=:id and is_active=true"),
                         {"id": patient_id}).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Active patient not found.")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Upload a PDF, JPEG, or PNG document.")
    data = await file.read(MAX_BYTES + 1)
    if not data:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Maximum document size is 10 MB.")
    signatures = {
        "application/pdf": data.startswith(b"%PDF-"),
        "image/jpeg": data.startswith(b"\xff\xd8\xff"),
        "image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
    }
    if not signatures.get(file.content_type, False):
        raise HTTPException(status_code=415, detail="File contents do not match the declared document type.")
    filename = _safe_filename(file.filename)
    path = f"{patient_id}/{uuid4().hex}_{filename}"
    storage = _storage()
    try:
        storage.upload(path, data, file_options={"content-type": file.content_type, "upsert": "false"})
        row = db.execute(text("""
            insert into public.patient_documents
              (patient_id, document_type, storage_path, original_filename, content_type,
               file_size_bytes, uploaded_by)
            values (:patient_id, :document_type, :path, :filename, :content_type, :size, :actor)
            returning id, patient_id, document_type, original_filename, content_type,
                      file_size_bytes, verification_status, created_at
        """), {"patient_id": patient_id, "document_type": document_type, "path": path,
               "filename": filename, "content_type": file.content_type, "size": len(data),
               "actor": profile.id}).mappings().one()
        db.add(AuditLog(actor_profile_id=profile.id, action="patient_document.uploaded",
                        resource_type="patient_document", resource_id=str(row["id"]),
                        details={"patient_id": str(patient_id), "document_type": document_type}))
        db.commit()
        return dict(row)
    except Exception as exc:
        db.rollback()
        try:
            storage.remove([path])
        except Exception:
            pass
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=500, detail="Document upload could not be completed.") from exc
    finally:
        await file.close()


@router.get("/patients/{patient_id}/documents")
def list_patient_documents(
    patient_id: UUID,
    profile: Profile = Depends(require_roles(*STAFF_DOCUMENT_ROLES)),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.execute(text("""
        select id, patient_id, document_type, original_filename, content_type,
               file_size_bytes, verification_status, reviewed_by, reviewed_at,
               review_notes, uploaded_by, created_at
        from public.patient_documents where patient_id=:patient_id
        order by created_at desc
    """), {"patient_id": patient_id}).mappings().all()
    return [dict(row) for row in rows]


@router.get("/patient-documents/{document_id}/signed-url")
def get_document_signed_url(
    document_id: UUID,
    profile: Profile = Depends(require_roles(*STAFF_DOCUMENT_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    row = db.execute(text("select storage_path, original_filename from public.patient_documents where id=:id"),
                     {"id": document_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found.")
    try:
        signed = _storage().create_signed_url(row["storage_path"], 60)
        url = signed.get("signedURL") or signed.get("signedUrl")
        if not url:
            raise ValueError("Storage did not return a signed URL.")
        db.add(AuditLog(actor_profile_id=profile.id, action="patient_document.accessed",
                        resource_type="patient_document", resource_id=str(document_id),
                        details={"filename": row["original_filename"]}))
        db.commit()
        return {"url": url, "expires_in_seconds": 60, "filename": row["original_filename"]}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail="Could not create a temporary document link.") from exc


@router.patch("/patient-documents/{document_id}/review")
def review_patient_document(
    document_id: UUID,
    verification_status: str = Query(..., pattern="^(approved|rejected)$"),
    review_notes: str | None = Query(default=None, max_length=1000),
    profile: Profile = Depends(require_roles(*REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    row = db.execute(text("""
        update public.patient_documents
        set verification_status=:status, reviewed_by=:actor, reviewed_at=now(),
            review_notes=:notes, updated_at=now()
        where id=:id and verification_status='pending'
        returning id, patient_id, document_type, verification_status, reviewed_by, reviewed_at, review_notes
    """), {"id": document_id, "status": verification_status, "actor": profile.id,
           "notes": review_notes}).mappings().first()
    if not row:
        exists = db.execute(text("select id from public.patient_documents where id=:id"),
                            {"id": document_id}).first()
        if not exists:
            raise HTTPException(status_code=404, detail="Document not found.")
        raise HTTPException(status_code=409, detail="Only pending documents can be reviewed.")
    db.add(AuditLog(actor_profile_id=profile.id, action=f"patient_document.{verification_status}",
                    resource_type="patient_document", resource_id=str(document_id),
                    details={"review_notes": review_notes}))
    db.commit()
    return dict(row)


@router.get("/exports/bills.csv", summary="Export bills to CSV")
def export_bills_csv(
    bill_status: str | None = Query(default=None, alias="status", pattern="^(open|partially_paid|paid|void)$"),
    profile: Profile = Depends(require_roles("administrator", "cashier", "information_officer")),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    rows = db.execute(text("""
        select b.bill_number, b.patient_id, p.medical_record_number,
               p.first_name, p.last_name, b.status, b.subtotal, b.adjustments, b.total,
               coalesce(sum(case when pay.status='posted' then pay.amount else 0 end), 0) as paid,
               b.created_at
        from public.bills b
        join public.patients p on p.id=b.patient_id
        left join public.payments pay on pay.bill_id=b.id
        where (:bill_status is null or b.status=:bill_status)
        group by b.id, p.id
        order by b.created_at desc
        limit 5000
    """), {"bill_status": bill_status}).mappings().all()
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["bill_number", "patient_id", "medical_record_number", "first_name", "last_name",
                     "status", "subtotal", "adjustments", "total", "paid", "balance", "created_at"])
    for row in rows:
        total, paid = Decimal(str(row["total"] or 0)), Decimal(str(row["paid"] or 0))
        balance = max(Decimal("0.00"), total - paid)
        writer.writerow([row["bill_number"], row["patient_id"], row["medical_record_number"],
                         row["first_name"], row["last_name"], row["status"], row["subtotal"],
                         row["adjustments"], row["total"], row["paid"], f"{balance:.2f}",
                         row["created_at"].isoformat() if row["created_at"] else ""])
    db.add(AuditLog(actor_profile_id=profile.id, action="data.exported", resource_type="bills",
                    resource_id="csv", details={"row_count": len(rows), "status": bill_status}))
    db.execute(text("""
        insert into public.export_audit_events(actor_profile_id, export_type, format, filters, row_count)
        values (:actor, 'bills', 'csv', cast(:filters as jsonb), :count)
    """), {"actor": profile.id, "filters": __import__("json").dumps({"status": bill_status}),
           "count": len(rows)})
    db.commit()
    stream.seek(0)
    filename = f"nexuscare-bills-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.csv"
    return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/exports/payments.csv", summary="Export payments to CSV")
def export_payments_csv(
    profile: Profile = Depends(require_roles("administrator", "cashier")),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    rows = db.execute(text("""
        select pay.id, b.bill_number, b.patient_id, pay.amount, pay.payment_method,
               pay.status, pay.received_at
        from public.payments pay join public.bills b on b.id=pay.bill_id
        order by pay.received_at desc limit 5000
    """)).mappings().all()
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["payment_id", "bill_number", "patient_id", "amount", "payment_method", "status", "received_at"])
    for row in rows:
        writer.writerow([row["id"], row["bill_number"], row["patient_id"], row["amount"],
                         row["payment_method"], row["status"],
                         row["received_at"].isoformat() if row["received_at"] else ""])
    db.add(AuditLog(actor_profile_id=profile.id, action="data.exported", resource_type="payments",
                    resource_id="csv", details={"row_count": len(rows)}))
    db.execute(text("""
        insert into public.export_audit_events(actor_profile_id, export_type, format, filters, row_count)
        values (:actor, 'payments', 'csv', '{}'::jsonb, :count)
    """), {"actor": profile.id, "count": len(rows)})
    db.commit()
    stream.seek(0)
    filename = f"nexuscare-payments-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.csv"
    return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})
