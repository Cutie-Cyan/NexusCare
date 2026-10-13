from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.core.notifications import notify_roles
from app.models import AuditLog, ConsultationNote, Encounter, NursingNote, Profile
from app.schemas.notes import (
    ConsultationNoteCreate, ConsultationNoteRead, NursingNoteCreate, NursingNoteRead,
)

router = APIRouter(tags=["consultation and nursing notes"])


def _active_encounter(db: Session, encounter_id: UUID) -> Encounter:
    encounter = db.scalar(select(Encounter).where(Encounter.id == encounter_id))
    if encounter is None:
        raise HTTPException(status_code=404, detail="Encounter not found.")
    return encounter


def _ensure_open(encounter: Encounter) -> None:
    if encounter.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Notes cannot be added to a closed encounter.")


def _audit(db: Session, profile: Profile, action: str, resource_type: str, resource_id: UUID, encounter_id: UUID) -> None:
    db.add(AuditLog(
        actor_profile_id=profile.id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details={"encounter_id": str(encounter_id)},
    ))


@router.get(
    "/encounters/{encounter_id}/consultation-notes",
    response_model=list[ConsultationNoteRead],
    summary="List consultation notes for an encounter",
)
def list_consultation_notes(
    encounter_id: UUID,
    profile: Profile = Depends(require_roles("doctor", "nurse")),
    db: Session = Depends(get_db),
) -> list[ConsultationNote]:
    _active_encounter(db, encounter_id)
    return list(db.scalars(
        select(ConsultationNote)
        .where(ConsultationNote.encounter_id == encounter_id)
        .order_by(ConsultationNote.created_at.asc())
    ).all())


@router.post(
    "/encounters/{encounter_id}/consultation-notes",
    response_model=ConsultationNoteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a consultation note",
)
def create_consultation_note(
    encounter_id: UUID,
    payload: ConsultationNoteCreate,
    profile: Profile = Depends(require_roles("doctor")),
    db: Session = Depends(get_db),
) -> ConsultationNote:
    encounter = _active_encounter(db, encounter_id)
    _ensure_open(encounter)
    note = ConsultationNote(
        encounter_id=encounter.id,
        author_id=profile.id,
        note_type=payload.note_type,
        content=payload.content,
    )
    db.add(note)
    db.flush()
    _audit(db, profile, "consultation_note.created", "consultation_note", note.id, encounter.id)
    notify_roles(db, {"nurse"}, "Consultation note added",
                 "A doctor added a note to an encounter. Review only if assigned and authorized.",
                 "clinical", exclude_profile_id=profile.id)
    db.commit()
    db.refresh(note)
    return note


@router.get(
    "/encounters/{encounter_id}/nursing-notes",
    response_model=list[NursingNoteRead],
    summary="List nursing notes for an encounter",
)
def list_nursing_notes(
    encounter_id: UUID,
    profile: Profile = Depends(require_roles("doctor", "nurse")),
    db: Session = Depends(get_db),
) -> list[NursingNote]:
    _active_encounter(db, encounter_id)
    return list(db.scalars(
        select(NursingNote)
        .where(NursingNote.encounter_id == encounter_id)
        .order_by(NursingNote.created_at.asc())
    ).all())


@router.post(
    "/encounters/{encounter_id}/nursing-notes",
    response_model=NursingNoteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a nursing note",
)
def create_nursing_note(
    encounter_id: UUID,
    payload: NursingNoteCreate,
    profile: Profile = Depends(require_roles("nurse")),
    db: Session = Depends(get_db),
) -> NursingNote:
    encounter = _active_encounter(db, encounter_id)
    _ensure_open(encounter)
    note = NursingNote(
        encounter_id=encounter.id,
        nurse_id=profile.id,
        note_type=payload.note_type,
        content=payload.content,
    )
    db.add(note)
    db.flush()
    _audit(db, profile, "nursing_note.created", "nursing_note", note.id, encounter.id)
    notify_roles(db, {"doctor"}, "Nursing note added",
                 "A nurse added a note to an encounter. Review only if assigned and authorized.",
                 "clinical", exclude_profile_id=profile.id)
    db.commit()
    db.refresh(note)
    return note
