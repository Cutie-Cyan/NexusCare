import pytest

from app.api.deps import ALL_ROLE_CODES, require_roles


def test_all_eight_roles_are_defined():
    assert ALL_ROLE_CODES == {
        "administrator",
        "information_officer",
        "doctor",
        "nurse",
        "cashier",
        "laboratory_staff",
        "pharmacy_staff",
        "patient",
    }


def test_unknown_role_fails_fast():
    with pytest.raises(ValueError, match="Unknown NexusCare role"):
        require_roles("superuser")
