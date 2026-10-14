from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import AuditLog, Profile

router = APIRouter(tags=["discounts and benefit estimates"])
REVIEW_ROLES = ("administrator", "cashier")
READ_ROLES = ("administrator", "information_officer", "cashier", "doctor", "nurse")


class DiscountApplicationCreate(BaseModel):
    patient_id: UUID
    bill_id: UUID | None = None
    document_id: UUID | None = None
    discount_type: str = Field(pattern="^(senior_citizen|pwd|philhealth|insurance|other)$")
    requested_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    review_notes: str | None = Field(default=None, max_length=1000)


class DiscountReview(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    approved_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    review_notes: str | None = Field(default=None, max_length=1000)


class BenefitEstimateCreate(BaseModel):
    patient_id: UUID
    bill_id: UUID | None = None
    estimate_type: str = Field(default="philhealth", pattern="^(philhealth|insurance|discount)$")
    estimated_coverage: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    estimated_discount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    rules_version: str = Field(default="manual-estimate-v1", min_length=1, max_length=80)

    @model_validator(mode="after")
    def validate_total(self):
        if self.estimated_coverage + self.estimated_discount < 0:
            raise ValueError("Estimated deductions cannot be negative.")
        return self


@router.post("/discount-applications", status_code=status.HTTP_201_CREATED)
def create_discount_application(
    payload: DiscountApplicationCreate,
    profile: Profile = Depends(require_roles("administrator", "cashier", "information_officer")),
    db: Session = Depends(get_db),
) -> dict:
    patient_exists = db.execute(
        text("select id from public.patients where id=:patient_id and is_active=true"),
        {"patient_id": payload.patient_id},
    ).first()
    if not patient_exists:
        raise HTTPException(status_code=404, detail="Active patient not found.")

    if payload.bill_id:
        bill = db.execute(
            text("select id, patient_id, total from public.bills where id=:bill_id"),
            {"bill_id": payload.bill_id},
        ).mappings().first()
        if not bill or bill["patient_id"] != payload.patient_id:
            raise HTTPException(status_code=422, detail="The bill must belong to the selected patient.")
        if payload.requested_amount > Decimal(str(bill["total"])):
            raise HTTPException(status_code=422, detail="Requested discount cannot exceed the bill total.")

    if payload.document_id:
        document = db.execute(
            text("select id, patient_id, verification_status from public.patient_documents where id=:id"),
            {"id": payload.document_id},
        ).mappings().first()
        if not document or document["patient_id"] != payload.patient_id:
            raise HTTPException(status_code=422, detail="Document must belong to the selected patient.")
        if document["verification_status"] != "approved":
            raise HTTPException(status_code=409, detail="Supporting document must be verified before applying the discount.")

    row = db.execute(text("""
        insert into public.discount_applications
          (patient_id, bill_id, document_id, discount_type, requested_amount, requested_by, review_notes)
        values (:patient_id, :bill_id, :document_id, :discount_type, :requested_amount, :requested_by, :review_notes)
        returning id, patient_id, bill_id, document_id, discount_type, requested_amount,
                  approved_amount, status, created_at
    """), {
        "patient_id": payload.patient_id, "bill_id": payload.bill_id,
        "document_id": payload.document_id, "discount_type": payload.discount_type,
        "requested_amount": payload.requested_amount, "requested_by": profile.id,
        "review_notes": payload.review_notes,
    }).mappings().one()
    db.add(AuditLog(
        actor_profile_id=profile.id, action="discount.requested",
        resource_type="discount_application", resource_id=str(row["id"]),
        details={"discount_type": payload.discount_type, "requested_amount": str(payload.requested_amount)},
    ))
    db.commit()
    return dict(row)


@router.patch("/discount-applications/{application_id}/review")
def review_discount_application(
    application_id: UUID,
    payload: DiscountReview,
    profile: Profile = Depends(require_roles(*REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    row = db.execute(text("""
        select id, patient_id, bill_id, requested_amount, status
        from public.discount_applications where id=:id for update
    """), {"id": application_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Discount application not found.")
    if row["status"] != "pending":
        raise HTTPException(status_code=409, detail="Only pending applications can be reviewed.")
    approved_amount = payload.approved_amount if payload.status == "approved" else Decimal("0.00")
    if approved_amount > Decimal(str(row["requested_amount"])):
        raise HTTPException(status_code=422, detail="Approved amount cannot exceed requested amount.")
    if row["bill_id"]:
        bill_total = db.execute(text("select total from public.bills where id=:id"), {"id": row["bill_id"]}).scalar_one()
        if approved_amount > Decimal(str(bill_total)):
            raise HTTPException(status_code=422, detail="Approved amount cannot exceed the bill total.")
    updated = db.execute(text("""
        update public.discount_applications
        set status=:status, approved_amount=:approved_amount, reviewed_by=:reviewed_by,
            reviewed_at=now(), review_notes=:review_notes, updated_at=now()
        where id=:id
        returning id, patient_id, bill_id, discount_type, requested_amount, approved_amount,
                  status, reviewed_by, reviewed_at, review_notes
    """), {
        "id": application_id, "status": payload.status, "approved_amount": approved_amount,
        "reviewed_by": profile.id, "review_notes": payload.review_notes,
    }).mappings().one()
    db.add(AuditLog(
        actor_profile_id=profile.id, action=f"discount.{payload.status}",
        resource_type="discount_application", resource_id=str(application_id),
        details={"approved_amount": str(approved_amount), "review_notes": payload.review_notes},
    ))
    db.commit()
    return dict(updated)


@router.get("/discount-applications")
def list_discount_applications(
    application_status: str | None = None,
    patient_id: UUID | None = None,
    profile: Profile = Depends(require_roles(*READ_ROLES)),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = """
        select id, patient_id, bill_id, document_id, discount_type, requested_amount,
               approved_amount, status, requested_by, reviewed_by, reviewed_at, review_notes, created_at
        from public.discount_applications where (:patient_id is null or patient_id=:patient_id)
          and (:application_status is null or status=:application_status)
        order by created_at desc limit 200
    """
    rows = db.execute(text(query), {"patient_id": patient_id, "application_status": application_status}).mappings().all()
    return [dict(row) for row in rows]


@router.post("/benefit-estimates", status_code=status.HTTP_201_CREATED)
def create_benefit_estimate(
    payload: BenefitEstimateCreate,
    profile: Profile = Depends(require_roles("administrator", "cashier", "information_officer")),
    db: Session = Depends(get_db),
) -> dict:
    if payload.bill_id:
        bill = db.execute(
            text("select patient_id, total from public.bills where id=:id"),
            {"id": payload.bill_id},
        ).mappings().first()
        if not bill or bill["patient_id"] != payload.patient_id:
            raise HTTPException(status_code=422, detail="The bill must belong to the selected patient.")
        gross = Decimal(str(bill["total"]))
    else:
        gross = Decimal("0.00")
        raise HTTPException(status_code=422, detail="A bill is required so the estimate is based on a recorded charge.")
    deductions = payload.estimated_coverage + payload.estimated_discount
    if deductions > gross:
        raise HTTPException(status_code=422, detail="Estimated coverage and discounts cannot exceed the bill total.")
    balance = gross - deductions
    row = db.execute(text("""
        insert into public.benefit_estimates
          (patient_id, bill_id, estimate_type, gross_amount, estimated_coverage,
           estimated_discount, estimated_patient_balance, rules_version, calculated_by)
        values (:patient_id, :bill_id, :estimate_type, :gross, :coverage, :discount, :balance, :rules_version, :actor)
        returning id, patient_id, bill_id, estimate_type, gross_amount, estimated_coverage,
                  estimated_discount, estimated_patient_balance, rules_version, disclaimer, created_at
    """), {
        "patient_id": payload.patient_id, "bill_id": payload.bill_id,
        "estimate_type": payload.estimate_type, "gross": gross,
        "coverage": payload.estimated_coverage, "discount": payload.estimated_discount,
        "balance": balance, "rules_version": payload.rules_version, "actor": profile.id,
    }).mappings().one()
    db.add(AuditLog(
        actor_profile_id=profile.id, action="benefit_estimate.created",
        resource_type="benefit_estimate", resource_id=str(row["id"]),
        details={"estimate_type": payload.estimate_type, "rules_version": payload.rules_version},
    ))
    db.commit()
    return dict(row)


@router.get("/benefit-estimates")
def list_benefit_estimates(
    patient_id: UUID | None = None,
    profile: Profile = Depends(require_roles(*READ_ROLES)),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.execute(text("""
        select id, patient_id, bill_id, estimate_type, gross_amount, estimated_coverage,
               estimated_discount, estimated_patient_balance, rules_version, disclaimer, created_at
        from public.benefit_estimates where (:patient_id is null or patient_id=:patient_id)
        order by created_at desc limit 200
    """), {"patient_id": patient_id}).mappings().all()
    return [dict(row) for row in rows]
