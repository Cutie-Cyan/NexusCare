from app.main import app


def test_patient_and_admission_routes_are_registered():
    paths = set(app.openapi()["paths"])
    assert "/api/v1/patients" in paths
    assert "/api/v1/patients/{patient_id}" in paths
    assert "/api/v1/wards" in paths
    assert "/api/v1/beds" in paths
    assert "/api/v1/admissions" in paths
    assert "/api/v1/admissions/{admission_id}/discharge" in paths
