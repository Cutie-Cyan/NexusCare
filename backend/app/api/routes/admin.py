from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import AuditLog, Profile

router = APIRouter(prefix="/admin", tags=["administration"])


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
