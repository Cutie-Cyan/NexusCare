from fastapi import APIRouter, Depends

from app.api.deps import require_roles
from app.models import Profile

router = APIRouter(prefix="/admin", tags=["administration"])


@router.get("/access-check")
def administrator_access_check(
    profile: Profile = Depends(require_roles("administrator")),
) -> dict[str, str]:
    """Small protected endpoint to verify role assignment before Phase 3."""
    return {"status": "authorized", "profile_id": str(profile.id)}
