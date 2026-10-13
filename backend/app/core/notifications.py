from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Notification, Profile, Role, UserRole


def notify_roles(
    db: Session,
    role_codes: set[str],
    title: str,
    message: str,
    category: str,
    exclude_profile_id: UUID | None = None,
) -> int:
    if not role_codes:
        return 0
    statement = (
        select(Profile.id)
        .join(UserRole, UserRole.profile_id == Profile.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Profile.is_active.is_(True), Role.code.in_(role_codes))
        .distinct()
    )
    if exclude_profile_id:
        statement = statement.where(Profile.id != exclude_profile_id)
    recipient_ids = db.scalars(statement).all()
    for recipient_id in recipient_ids:
        db.add(Notification(
            recipient_profile_id=recipient_id,
            title=title,
            message=message,
            category=category,
        ))
    return len(recipient_ids)


def notify_profiles(
    db: Session,
    profile_ids: set[UUID],
    title: str,
    message: str,
    category: str,
    exclude_profile_id: UUID | None = None,
) -> int:
    profile_ids = {profile_id for profile_id in profile_ids if profile_id != exclude_profile_id}
    if not profile_ids:
        return 0
    recipient_ids = db.scalars(select(Profile.id).where(
        Profile.id.in_(profile_ids), Profile.is_active.is_(True)
    )).all()
    for recipient_id in recipient_ids:
        db.add(Notification(
            recipient_profile_id=recipient_id,
            title=title,
            message=message,
            category=category,
        ))
    return len(recipient_ids)
