import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from supabase import create_client

from app.api.deps import get_profile_roles, require_roles
from app.core.config import get_settings
from app.db.session import get_db
from app.models import AuditLog, Department, Patient, Profile, Role, UserRole
from app.schemas.admin import StaffCreate, StaffRolesUpdate, StaffStatusUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["administration"])


def _audit(db: Session, actor: Profile, action: str, resource_type: str, resource_id: UUID, details: dict | None = None) -> None:
    db.add(AuditLog(
        actor_profile_id=actor.id, action=action, resource_type=resource_type,
        resource_id=str(resource_id), details=details or {},
    ))


@router.get("/access-check")
def administrator_access_check(
    profile: Profile = Depends(require_roles("administrator")),
) -> dict[str, str]:
    """Verify role assignment before accessing administrative operations."""
    return {"status": "authorized", "profile_id": str(profile.id)}


@router.get("/audit-logs", summary="Search the administrative audit trail")
def list_audit_logs(
    action: str | None = Query(default=None, min_length=1, max_length=100),
    resource_type: str | None = Query(default=None, min_length=1, max_length=100),
    actor_profile_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    profile: Profile = Depends(require_roles("administrator")),
    db: Session = Depends(get_db),
) -> list[dict]:
    statement = select(AuditLog)
    if action:
        statement = statement.where(AuditLog.action == action)
    if resource_type:
        statement = statement.where(AuditLog.resource_type == resource_type)
    if actor_profile_id:
        statement = statement.where(AuditLog.actor_profile_id == actor_profile_id)
    rows = db.scalars(
        statement.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return [{
        "id": str(row.id),
        "actor_profile_id": str(row.actor_profile_id) if row.actor_profile_id else None,
        "action": row.action,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "details": row.details or {},
        "ip_address": row.ip_address,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    } for row in rows]


@router.get("/staff", summary="List staff profiles and role assignments")
def list_staff(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    profile: Profile = Depends(require_roles("administrator")),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.scalars(select(Profile).order_by(Profile.full_name).offset(offset).limit(limit)).all()
    return [{
        "profile_id": str(row.id),
        "full_name": row.full_name,
        "email": row.email,
        "department_id": str(row.department_id) if row.department_id else None,
        "is_active": row.is_active,
        "roles": get_profile_roles(row.id, db),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    } for row in rows]


@router.post("/staff", status_code=201, summary="Create a staff or linked patient account")
def create_staff_account(
    payload: StaffCreate,
    profile: Profile = Depends(require_roles("administrator")),
    db: Session = Depends(get_db),
) -> dict:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise HTTPException(status_code=503, detail="Staff provisioning requires server-only SUPABASE_SECRET_KEY configuration.")
    roles = db.scalars(select(Role).where(Role.code.in_(payload.role_codes))).all()
    role_map = {role.code: role for role in roles}
    if set(role_map) != set(payload.role_codes):
        raise HTTPException(status_code=422, detail="One or more role codes do not exist.")
    if "patient" in payload.role_codes and not payload.patient_id:
        raise HTTPException(status_code=422, detail="Patient accounts must be linked to an existing patient record.")
    if "patient" not in payload.role_codes and payload.patient_id:
        raise HTTPException(status_code=422, detail="patient_id can only be supplied when assigning the patient role.")
    if payload.department_id and db.scalar(select(Department.id).where(
        Department.id == payload.department_id, Department.is_active.is_(True)
    )) is None:
        raise HTTPException(status_code=422, detail="Active department not found.")
    patient = None
    if payload.patient_id:
        patient = db.scalar(select(Patient).where(
            Patient.id == payload.patient_id, Patient.is_active.is_(True)
        ).with_for_update())
        if patient is None:
            raise HTTPException(status_code=404, detail="Active patient not found.")
        if patient.patient_profile_id is not None:
            raise HTTPException(status_code=409, detail="Patient already has a linked login account.")

    try:
        admin_client = create_client(settings.supabase_url, settings.supabase_secret_key)
        auth_response = admin_client.auth.admin.create_user({
            "email": payload.email,
            "password": payload.initial_password,
            "email_confirm": True,
            "user_metadata": {"full_name": payload.full_name},
        })
        auth_user = getattr(auth_response, "user", None)
        if auth_user is None:
            raise HTTPException(status_code=502, detail="Supabase Auth did not return the created user.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Supabase Auth account creation failed. Check server configuration and duplicate email.") from exc

    try:
        staff_profile = Profile(
            auth_user_id=UUID(str(auth_user.id)), full_name=payload.full_name,
            email=payload.email, department_id=payload.department_id, is_active=True,
        )
        db.add(staff_profile)
        db.flush()
        for role_code in payload.role_codes:
            db.add(UserRole(profile_id=staff_profile.id, role_id=role_map[role_code].id, assigned_by=profile.id))
        if patient is not None:
            patient.patient_profile_id = staff_profile.id
        _audit(db, profile, "staff_account.created", "profile", staff_profile.id, {
            "email": payload.email, "role_codes": payload.role_codes,
            "department_id": str(payload.department_id) if payload.department_id else None,
            "patient_id": str(patient.id) if patient else None,
        })
        db.commit()
        db.refresh(staff_profile)
        return {
            "profile_id": str(staff_profile.id), "auth_user_id": str(staff_profile.auth_user_id),
            "email": staff_profile.email, "full_name": staff_profile.full_name,
            "roles": payload.role_codes, "is_active": staff_profile.is_active,
        }
    except Exception as exc:
        db.rollback()
        try:
            admin_client.auth.admin.delete_user(str(auth_user.id))
        except Exception:  # noqa: BLE001 - preserve the original database failure
            logger.exception("Failed to roll back Supabase Auth user after profile creation failure")
        if isinstance(exc, HTTPException):
            raise
        if isinstance(exc, IntegrityError):
            raise HTTPException(status_code=409, detail="Staff account conflicts with an existing record.") from exc
        raise HTTPException(status_code=500, detail="Staff profile creation failed; the Auth user was rolled back when possible.") from exc


@router.patch("/staff/{profile_id}/roles", summary="Replace a staff member's role assignments")
def update_staff_roles(
    profile_id: UUID,
    payload: StaffRolesUpdate,
    profile: Profile = Depends(require_roles("administrator")),
    db: Session = Depends(get_db),
) -> dict:
    target = db.scalar(select(Profile).where(Profile.id == profile_id).with_for_update())
    if target is None:
        raise HTTPException(status_code=404, detail="Staff profile not found.")
    roles = db.scalars(select(Role).where(Role.code.in_(payload.role_codes))).all()
    role_map = {role.code: role for role in roles}
    if set(role_map) != set(payload.role_codes):
        raise HTTPException(status_code=422, detail="One or more role codes do not exist.")
    if "patient" in payload.role_codes:
        patient = db.scalar(select(Patient.id).where(Patient.patient_profile_id == target.id))
        if patient is None:
            raise HTTPException(status_code=422, detail="Patient role requires a linked patient record.")
    db.query(UserRole).filter(UserRole.profile_id == target.id).delete(synchronize_session=False)
    for role_code in payload.role_codes:
        db.add(UserRole(profile_id=target.id, role_id=role_map[role_code].id, assigned_by=profile.id))
    _audit(db, profile, "staff_roles.updated", "profile", target.id, {"role_codes": payload.role_codes})
    db.commit()
    return {"profile_id": str(target.id), "roles": payload.role_codes}


@router.patch("/staff/{profile_id}/status", summary="Activate or deactivate a staff profile")
def update_staff_status(
    profile_id: UUID,
    payload: StaffStatusUpdate,
    profile: Profile = Depends(require_roles("administrator")),
    db: Session = Depends(get_db),
) -> dict:
    target = db.scalar(select(Profile).where(Profile.id == profile_id).with_for_update())
    if target is None:
        raise HTTPException(status_code=404, detail="Staff profile not found.")
    if target.id == profile.id and not payload.is_active:
        raise HTTPException(status_code=409, detail="You cannot deactivate your own administrator profile.")
    target.is_active = payload.is_active
    _audit(db, profile, "staff_status.updated", "profile", target.id, {"is_active": target.is_active})
    db.commit()
    return {"profile_id": str(target.id), "is_active": target.is_active}
