from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.models import Admission, Encounter, Profile, Role, UserRole

ALL_ROLE_CODES = {
    "administrator",
    "information_officer",
    "doctor",
    "nurse",
    "cashier",
    "laboratory_staff",
    "pharmacy_staff",
    "patient",
}


def get_current_profile(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    profile = db.scalar(
        select(Profile).where(
            Profile.auth_user_id == user.user_id,
            Profile.is_active.is_(True),
        )
    )
    if profile is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active NexusCare profile.")
    return profile


def require_roles(*allowed_roles: str) -> Callable:
    unknown = set(allowed_roles) - ALL_ROLE_CODES
    if unknown:
        raise ValueError(f"Unknown NexusCare role code(s): {', '.join(sorted(unknown))}")

    def dependency(
        profile: Profile = Depends(get_current_profile),
        db: Session = Depends(get_db),
    ) -> Profile:
        role_codes = set(
            db.scalars(
                select(Role.code)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.profile_id == profile.id)
            ).all()
        )
        if not role_codes.intersection(allowed_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")
        return profile

    return dependency


def get_profile_roles(profile_id: UUID, db: Session) -> list[str]:
    return list(
        db.scalars(
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.profile_id == profile_id)
            .order_by(Role.code)
        ).all()
    )


def ensure_encounter_access(profile: Profile, encounter: Encounter, db: Session) -> None:
    """Restrict clinical records to the assigned clinician or the encounter's department.

    Nurses and laboratory staff have no dedicated encounter-assignment table yet, so
    they must have an explicit matching department. Unscoped access is denied.
    """
    roles = set(get_profile_roles(profile.id, db))
    if "administrator" in roles:
        return
    if encounter.clinician_id == profile.id:
        return
    if encounter.department_id is not None and profile.department_id == encounter.department_id:
        return
    if encounter.admission_id is not None:
        admission = db.scalar(
            select(Admission).where(Admission.id == encounter.admission_id)
        )
        if admission is not None and admission.attending_doctor_id == profile.id:
            return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You are not assigned to this encounter or its department.",
    )
