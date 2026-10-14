from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.api.deps import ensure_encounter_access


def make_profile(*, department_id=None):
    return SimpleNamespace(id=uuid4(), department_id=department_id)


def make_encounter(*, clinician_id=None, department_id=None, admission_id=None):
    return SimpleNamespace(
        id=uuid4(),
        clinician_id=clinician_id,
        department_id=department_id,
        admission_id=admission_id,
    )


def test_assigned_clinician_can_access_encounter(monkeypatch):
    profile = make_profile()
    encounter = make_encounter(clinician_id=profile.id)
    monkeypatch.setattr("app.api.deps.get_profile_roles", lambda *_: ["doctor"])

    ensure_encounter_access(profile, encounter, Mock())


def test_same_department_staff_can_access_encounter(monkeypatch):
    department_id = uuid4()
    profile = make_profile(department_id=department_id)
    encounter = make_encounter(department_id=department_id)
    monkeypatch.setattr("app.api.deps.get_profile_roles", lambda *_: ["nurse"])

    ensure_encounter_access(profile, encounter, Mock())


def test_unassigned_staff_is_denied(monkeypatch):
    profile = make_profile(department_id=uuid4())
    encounter = make_encounter(department_id=uuid4())
    monkeypatch.setattr("app.api.deps.get_profile_roles", lambda *_: ["doctor"])

    with pytest.raises(HTTPException) as exc:
        ensure_encounter_access(profile, encounter, Mock())

    assert exc.value.status_code == 403


def test_administrator_can_access_encounter(monkeypatch):
    profile = make_profile()
    encounter = make_encounter()
    monkeypatch.setattr("app.api.deps.get_profile_roles", lambda *_: ["administrator"])

    ensure_encounter_access(profile, encounter, Mock())


def test_attending_doctor_can_access_admission_encounter(monkeypatch):
    profile = make_profile()
    encounter = make_encounter(admission_id=uuid4())
    db = Mock()
    db.scalar.return_value = SimpleNamespace(attending_doctor_id=profile.id)
    monkeypatch.setattr("app.api.deps.get_profile_roles", lambda *_: ["doctor"])

    ensure_encounter_access(profile, encounter, db)
