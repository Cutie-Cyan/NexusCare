from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_profile_roles
from app.core.security import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.models import Profile

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me")
def read_current_identity(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = db.query(Profile).filter(
        Profile.auth_user_id == user.user_id,
        Profile.is_active.is_(True),
    ).one_or_none()
    if profile is None:
        return {
            "authenticated": True,
            "user_id": str(user.user_id),
            "email": user.email,
            "profile_complete": False,
            "roles": [],
        }
    return {
        "authenticated": True,
        "user_id": str(user.user_id),
        "profile_id": str(profile.id),
        "full_name": profile.full_name,
        "email": profile.email or user.email,
        "profile_complete": True,
        "roles": get_profile_roles(profile.id, db),
    }
