import pytest
from pydantic import ValidationError

from app.schemas.notes import ConsultationNoteCreate, NursingNoteCreate


def test_consultation_note_defaults_and_trims_content():
    note = ConsultationNoteCreate(content="  Patient reports improvement.  ")
    assert note.note_type == "progress"
    assert note.content == "Patient reports improvement."


def test_consultation_note_rejects_unknown_type():
    with pytest.raises(ValidationError):
        ConsultationNoteCreate(note_type="billing", content="Some note")


def test_consultation_note_rejects_blank_content():
    with pytest.raises(ValidationError):
        ConsultationNoteCreate(content="   ")


def test_nursing_note_defaults_and_trims_content():
    note = NursingNoteCreate(note_type="handover", content="  Handover completed. ")
    assert note.note_type == "handover"
    assert note.content == "Handover completed."


def test_nursing_note_rejects_unknown_type():
    with pytest.raises(ValidationError):
        NursingNoteCreate(note_type="prescription", content="Some note")


def test_nursing_note_rejects_blank_content():
    with pytest.raises(ValidationError):
        NursingNoteCreate(content=" ")
