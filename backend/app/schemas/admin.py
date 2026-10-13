from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class StaffCreate(BaseModel):
    email: str = Field(min_length=5, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    full_name: str = Field(min_length=2, max_length=180)
    initial_password: str = Field(min_length=12, max_length=128)
    role_codes: list[str] = Field(min_length=1, max_length=8)
    department_id: UUID | None = None
    patient_id: UUID | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Full name cannot be blank.")
        return value

    @field_validator("role_codes")
    @classmethod
    def normalize_roles(cls, values: list[str]) -> list[str]:
        normalized = [value.strip().lower() for value in values]
        if not all(normalized) or len(normalized) != len(set(normalized)):
            raise ValueError("Role codes must be nonblank and unique.")
        return normalized


class StaffRolesUpdate(BaseModel):
    role_codes: list[str] = Field(min_length=1, max_length=8)

    @field_validator("role_codes")
    @classmethod
    def normalize_roles(cls, values: list[str]) -> list[str]:
        normalized = [value.strip().lower() for value in values]
        if not all(normalized) or len(normalized) != len(set(normalized)):
            raise ValueError("Role codes must be nonblank and unique.")
        return normalized


class StaffStatusUpdate(BaseModel):
    is_active: bool
