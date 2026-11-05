from pathlib import Path

import pandas as pd
import pytest

from fhir_prototype.bundle_index import BundleIndex, UnresolvedReferenceError
from fhir_prototype.bundle_loader import load_bundle
from fhir_prototype.frames import (
    ENCOUNTER_COLUMNS,
    PATIENT_COLUMNS,
    encounters_frame,
    patients_frame,
    observations_frame, OBSERVATION_COLUMNS
)
from helpers import BASE, make_bundle

FIXTURES = Path(__file__).parent / "fixtures"
BASE = "https://fhir.example.org"
PATIENT = {"resourceType": "Patient", "id": "p1"}
DEVICE_METRIC = {
    "resourceType": "DeviceMetric",
    "id": "dm1",
    "category": "setting",
}


def make_encounter(**overrides):
    encounter = {
        "resourceType": "Encounter",
        "id": "e1",
        "identifier": [{"system": "urn:eid", "value": "E-1"}],
        "status": "finished",
        "class": {"code": "IMP"},
        "subject": {"reference": f"{BASE}/Patient/p1"},
        "period": {
            "start": "2024-01-15T09:00:00+01:00",
            "end": "2024-01-19T12:00:00+01:00",
        },
    }
    encounter.update(overrides)
    return encounter


ENCOUNTER = make_encounter()


def make_observation(**overrides):
    observation = {
        "resourceType": "Observation",
        "id": "o1",
        "meta": {"profile": ["https://example.org/StructureDefinition/heartrate"]},
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]},
        "subject": {"reference": f"{BASE}/Patient/p1"},
        "encounter": {"reference": f"{BASE}/Encounter/e1"},
        "effectiveDateTime": "2024-01-15T09:00:00+01:00",
        "valueQuantity": {"value": 80, "unit": "/min", "code": "/min"},
    }
    observation.update(overrides)
    return observation


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


def test_observations_frame_resolves_patient_and_encounters():
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, make_observation()))

    df = observations_frame(index)

    row = df.iloc[0]
    assert row["observation_id"] == "o1"
    assert row["patient_id"] == "p1"
    assert row["encounter_id"] == "e1"


@pytest.mark.parametrize("field, reference", [
    ("subject", f"{BASE}/Patient/ghost"),
    ("encounter", f"{BASE}/Encounter/ghost"),
    ("device", f"{BASE}/DeviceMetric/ghost"),
])
def test_observations_frame_fails_on_unknown_reference(field, reference):
    observation = make_observation(**{field: {"reference": reference}})
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, observation))

    with pytest.raises(UnresolvedReferenceError):
        observations_frame(index)


def test_observations_frame_without_observations_still_has_columns():
    index = BundleIndex(make_bundle(PATIENT))

    df = observations_frame(index)

    assert df.empty
    assert list(df.columns) == OBSERVATION_COLUMNS


def test_observations_frame_from_fixtures():
    index = BundleIndex(load_bundle(FIXTURES / "bundle_max_1.json"))

    df = observations_frame(index)
    assert len(df) == 240
    assert df["patient_id"].nunique() == 1
    assert df["encounter_id"].nunique() == 1


def test_observations_frame_has_profile_and_status():
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, make_observation()))

    df = observations_frame(index)

    row = df.iloc[0]
    assert row["profile"] == "https://example.org/StructureDefinition/heartrate"
    assert row["status"] == "final"


def test_observations_frame_profile_is_none_without_meta():
    observation = make_observation()
    del observation["meta"]
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, observation))

    df = observations_frame(index)

    row = df.iloc[0]
    assert row["profile"] is None


def test_observations_frame_takes_start_from_effective_date_time():
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, make_observation()))

    df = observations_frame(index)

    row = df.iloc[0]
    assert row["start"] == "2024-01-15T09:00:00+01:00"
    assert row["end"] is None


def test_observations_frame_takes_start_and_end_from_effective_period():
    observation = make_observation(effectivePeriod={
        "start": "2024-01-15T09:00:00+01:00",
        "end": "2024-01-15T09:01:00+01:00",
    })
    del observation["effectiveDateTime"]
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, observation))

    df = observations_frame(index)

    row = df.iloc[0]
    assert row["start"] == "2024-01-15T09:00:00+01:00"
    assert row["end"] == "2024-01-15T09:01:00+01:00"


def test_observations_frame_has_start_for_every_row_in_max_bundle():
    index = BundleIndex(load_bundle(FIXTURES / "bundle_max_1.json"))

    df = observations_frame(index)
    assert df["start"].notna().all()


def test_observations_frame_has_codes_as_system_pipe_code():
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, make_observation()))

    df = observations_frame(index)

    row = df.iloc[0]
    assert row["codes"] == ["http://loinc.org|8867-4"]


def test_observations_frame_keeps_all_codings_in_order():
    observation = make_observation(code={"coding": [
        {
            "system": "http://snomed.info/sct",
            "code": "260385009",
            "display": "Negative"
        }, {
            "system": "https://acme.lab/resultcodes",
            "code": "NEG",
            "display": "Negative"
        }
    ]})
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, observation))

    df = observations_frame(index)

    row = df.iloc[0]
    assert row["codes"] == [
        "http://snomed.info/sct|260385009",
        "https://acme.lab/resultcodes|NEG",
    ]


def test_observations_frame_codes_is_empty_list_without_code():
    observation = make_observation()
    del observation["code"]
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, observation))

    df = observations_frame(index)
    row = df.iloc[0]
    assert row["codes"] == []


def test_observations_frame_max_bundle_has_code_for_every_row():
    index = BundleIndex(load_bundle(FIXTURES / "bundle_max_1.json"))

    df = observations_frame(index)
    assert df["codes"].map(len).min() >= 1


def test_observations_frame_reads_value_quantity():
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, make_observation()))

    df = observations_frame(index)

    row = df.iloc[0]
    assert row["value_type"] == "Quantity"
    assert row["value_num"] == 80
    assert row["value_unit"] == "/min"


def test_observations_frame_reads_value_integer():
    observation = make_observation(valueInteger=7)
    del observation["valueQuantity"]
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, observation))

    df = observations_frame(index)

    row = df.iloc[0]
    assert row["value_type"] == "Integer"
    assert row["value_num"] == 7


def test_observations_frame_reads_value_codeable_concept():
    observation = make_observation(valueCodeableConcept={
        "coding": [{"system": "http://loinc.org", "code": "LA33966-5", "display": "Deep sedation"}],
        "text": "-4",
    })
    del observation["valueQuantity"]
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, observation))

    df = observations_frame(index)

    row = df.iloc[0]
    assert row["value_type"] == "CodeableConcept"
    assert row["value_codes"] == ["http://loinc.org|LA33966-5"]
    assert row["value_text"] == "-4"
    assert pd.isna(row["value_num"])


def test_observations_frame_value_is_empty_without_value():
    observation = make_observation()
    del observation["valueQuantity"]
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, observation))

    df = observations_frame(index)

    row = df.iloc[0]
    assert pd.isna(row["value_type"])
    assert pd.isna(row["value_num"])
    assert row["value_codes"] == []


def test_observations_frame_max_bundle_value_types():
    index = BundleIndex(load_bundle(FIXTURES / "bundle_max_1.json"))

    df = observations_frame(index)

    assert df["value_type"].value_counts().to_dict() == {
        "Quantity": 208,
        "Integer": 24,
        "CodeableConcept": 8,
    }


def test_observations_frame_reads_device_category():
    observation = make_observation(device={"reference": f"{BASE}/DeviceMetric/dm1"})
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, DEVICE_METRIC, observation))

    df = observations_frame(index)

    row = df.iloc[0]
    assert row["device_category"] == "setting"


def test_observations_frame_from_device_category_is_none_without_device():
    observation = make_observation(deviceCategory={})
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, observation))

    df = observations_frame(index)

    row = df.iloc[0]
    assert pd.isna(row["device_category"])


PEEP_PROFILE = (
    "https://www.medizininformatik-initiative.de/fhir/ext/modul-icu/"
    "StructureDefinition/mii-pr-icu-vent-positiv-endexspiratorischer-druck"
)


def test_observations_frame_max_bundle_distinguishes_peep_setting_and_measurement():
    index = BundleIndex(load_bundle(FIXTURES / "bundle_max_1.json"))

    df = observations_frame(index)

    peep = df[df["profile"] == PEEP_PROFILE]
    assert len(peep) > 0
    assert set(peep["device_category"]) == {"setting", "measurement"}


def test_observations_frame_columns():
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, make_observation()))

    df = observations_frame(index)

    assert list(df.columns) == [
        "observation_id",
        "patient_id",
        "encounter_id",
        "profile",
        "status",
        "codes",
        "start",
        "end",
        "value_type",
        "value_num",
        "value_unit",
        "value_codes",
        "value_text",
        "device_category"
    ]
