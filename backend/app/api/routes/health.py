from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Check API process health")
def health_check() -> dict[str, str]:
    """Checks API process only; does not claim database/auth connectivity."""
    return {"status": "ok", "service": "nexuscare-api", "phase": "10"}
