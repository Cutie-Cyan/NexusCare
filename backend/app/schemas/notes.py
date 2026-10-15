from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ConsultationNoteType = Literal["initial", "progress", "follow_up", "discharge"]
NursingNoteType = Literal["assessment", "progress", "intervention", "handover"]


class ConsultationNoteCreate(BaseModel):
    note_type: ConsultationNoteType = "progress"
    content: str = Field(min_length=2, max_length=20000)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Note content must contain at least 2 characters.")
        return value


class ConsultationNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    encounter_id: UUID
    author_id: UUID
    note_type: str
    content: str
    created_at: datetime
    amended_at: datetime | None


class NursingNoteCreate(BaseModel):
    note_type: NursingNoteType = "progress"
    content: str = Field(min_length=2, max_length=20000)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Note content must contain at least 2 characters.")
        return value


class NursingNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    encounter_id: UUID
    nurse_id: UUID
    note_type: str
    content: str
    created_at: datetime
