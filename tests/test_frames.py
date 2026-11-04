from pathlib import Path

from helpers import make_bundle

from fhir_prototype.bundle_index import BundleIndex
from fhir_prototype.bundle_loader import load_bundle
from fhir_prototype.frames import PATIENT_COLUMNS, patients_frame

FIXTURES = Path(__file__).parent / "fixtures"


def test_patients_frame_has_one_row_per_patient():
    patient = {
        "resourceType": "Patient",
        "id": "p1",
        "identifier": [{"system": "urn:pid", "value": "P-1"}],
        "gender": "female",
        "birthDate": "2001-07-02",
    }
    index = BundleIndex(make_bundle(patient))

    df = patients_frame(index)

    assert df.to_dict("records") == [{
        "patient_id": "p1",
        "identifier_system": "urn:pid",
        "identifier_value": "P-1",
        "gender": "female",
        "birth_date": "2001-07-02",
    }]


def test_patients_frame_fills_missing_fields_with_none():
    index = BundleIndex(make_bundle({"resourceType": "Patient", "id": "p1"}))

    df = patients_frame(index)

    row = df.iloc[0]
    assert row["identifier_value"] is None
    assert row["gender"] is None


def test_patients_frame_without_patients_still_has_columns():
    index = BundleIndex(make_bundle({"resourceType": "Observation", "id": "o1"}))

    df = patients_frame(index)

    assert df.empty
    assert list(df.columns) == PATIENT_COLUMNS


def test_patients_frame_from_min_bundle():
    index = BundleIndex(load_bundle(FIXTURES / "bundle_min.json"))

    df = patients_frame(index)

    assert len(df) == 1
    assert df.iloc[0]["identifier_value"] == "P-0987665"