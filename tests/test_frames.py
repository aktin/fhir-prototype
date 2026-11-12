import pytest

from fhir_prototype.bundle_index import BundleIndex, UnresolvedReferenceError
from fhir_prototype.bundle_loader import load_bundle
from fhir_prototype.frames import (
    ENCOUNTER_COLUMNS,
    PATIENT_COLUMNS,
    bundle_to_frames,
    encounters_frame,
    patients_frame,
)
from helpers import BASE, ENCOUNTER, FIXTURES, PATIENT, make_bundle, make_encounter


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


def test_encounters_frame_has_one_row_per_encounter():
    index = BundleIndex(make_bundle(PATIENT, make_encounter()))

    df = encounters_frame(index)

    assert df.to_dict("records") == [{
        "encounter_id": "e1",
        "patient_id": "p1",
        "identifier_system": "urn:eid",
        "identifier_value": "E-1",
        "status": "finished",
        "class_code": "IMP",
        "start": "2024-01-15T09:00:00+01:00",
        "end": "2024-01-19T12:00:00+01:00",
    }]


def test_encounters_frame_allows_open_period():
    encounter = make_encounter(status="in-progress",
                               period={"start": "2024-06-03T14:30:00+02:00"})
    index = BundleIndex(make_bundle(PATIENT, encounter))

    df = encounters_frame(index)

    assert df.iloc[0]["end"] is None


def test_encounters_frame_fails_on_unknown_subject():
    encounter = make_encounter(subject={"reference": f"{BASE}/Patient/ghost"})
    index = BundleIndex(make_bundle(PATIENT, encounter))

    with pytest.raises(UnresolvedReferenceError):
        encounters_frame(index)


def test_encounters_frame_without_encounters_still_has_columns():
    index = BundleIndex(make_bundle(PATIENT))

    df = encounters_frame(index)

    assert df.empty
    assert list(df.columns) == ENCOUNTER_COLUMNS


@pytest.mark.parametrize("fixture, expected_end", [
    ("bundle_min.json", None),
    ("bundle_max_1.json", "2024-01-19T12:00:00+01:00"),
])
def test_encounters_frame_from_fixtures(fixture, expected_end):
    index = BundleIndex(load_bundle(FIXTURES / fixture))

    df = encounters_frame(index)

    assert len(df) == 1
    assert df.iloc[0]["end"] == expected_end


def test_bundle_to_frames_builds_patient_and_encounter_tables():
    index = BundleIndex(load_bundle(FIXTURES / "bundle_max_1.json"))

    frames = bundle_to_frames(index)

    assert len(frames.patients) == 1
    assert len(frames.encounters) == 1


def test_bundle_frames_has_only_patients_and_encounters():
    frames = bundle_to_frames(BundleIndex(make_bundle(PATIENT, ENCOUNTER)))

    assert list(vars(frames)) == ["patients", "encounters"]
