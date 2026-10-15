from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.admin import router as admin_router
from app.api.routes.admissions import router as admissions_router
from app.api.routes.auth import router as auth_router
from app.api.routes.billing import router as billing_router
from app.api.routes.clinical import router as clinical_router
from app.api.routes.documents_exports import router as documents_exports_router
from app.api.routes.finance_extensions import router as finance_extensions_router
from app.api.routes.health import router as health_router
from app.api.routes.laboratory import router as laboratory_router
from app.api.routes.notes import router as notes_router
from app.api.routes.operations import router as operations_router
from app.api.routes.patients import router as patients_router
from app.api.routes.pharmacy import router as pharmacy_router
from app.api.routes.receipts_exports import router as receipts_exports_router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    description="NexusCare hospital information and resource management REST API.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(admin_router, prefix=settings.api_v1_prefix)
app.include_router(patients_router, prefix=settings.api_v1_prefix)
app.include_router(admissions_router, prefix=settings.api_v1_prefix)
app.include_router(clinical_router, prefix=settings.api_v1_prefix)
app.include_router(notes_router, prefix=settings.api_v1_prefix)
app.include_router(laboratory_router, prefix=settings.api_v1_prefix)
app.include_router(pharmacy_router, prefix=settings.api_v1_prefix)
app.include_router(billing_router, prefix=settings.api_v1_prefix)
app.include_router(finance_extensions_router, prefix=settings.api_v1_prefix)
app.include_router(documents_exports_router, prefix=settings.api_v1_prefix)
app.include_router(receipts_exports_router, prefix=settings.api_v1_prefix)
app.include_router(operations_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["root"], include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs"}
