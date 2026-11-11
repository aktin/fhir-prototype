import pandas as pd

from fhir_prototype.bundle_loader import load_bundle
from fhir_prototype.frames import bundle_to_frames
from fhir_prototype.processing import process
from helpers import ENCOUNTER, PATIENT, make_bundle, make_observation, FIXTURES, make_encounter, make_procedure


def test_process_converts_observation_start_to_utc():
    frames = bundle_to_frames(make_bundle(PATIENT, ENCOUNTER, make_observation()))

    processed = process(frames)

    start = processed.observations.iloc[0]["start"]
    assert start == pd.Timestamp("2024-01-15T08:00:00Z")
    assert str(start.tz) == "UTC"


def test_process_keeps_missing_observation_end_empty():
    frames = bundle_to_frames(make_bundle(PATIENT, ENCOUNTER, make_observation()))

    processed = process(frames)

    assert pd.isna(processed.observations.iloc[0]["end"])


def test_process_converts_observation_end_to_utc():
    observation = make_observation(effectivePeriod={
        "start": "2024-01-15T09:00:00+01:00",
        "end": "2024-01-15T09:01:00+01:00",
    })
    del observation["effectiveDateTime"]
    frames = bundle_to_frames(make_bundle(PATIENT, ENCOUNTER, observation))

    processed = process(frames)

    end = processed.observations.iloc[0]["end"]
    assert end == pd.Timestamp("2024-01-15T08:01:00Z")
    assert str(end.tz) == "UTC"


def test_process_handles_dst_change_in_max_bundle_2():
    frames = bundle_to_frames(load_bundle(FIXTURES / "bundle_max_2.json"))

    processed_observations = process(frames).observations

    assert str(processed_observations["start"].dt.tz) == "UTC"
    assert processed_observations["start"].notna().all()

    def start_of(observation_id):
        rows = processed_observations[processed_observations["observation_id"] == observation_id]
        return rows.iloc[0]["start"]

    assert start_of("icu-vent-map-measured-bd30493bd56f") == pd.Timestamp("2024-03-31T00:29:00Z")
    assert start_of("icu-rass-a6170189a93b") == pd.Timestamp("2024-03-31T08:00:00Z")


def test_process_converts_encounter_times_to_utc():
    frames = bundle_to_frames(make_bundle(PATIENT, make_encounter()))

    processed = process(frames)

    row = processed.encounters.iloc[0]
    assert row["start"] == pd.Timestamp("2024-01-15T08:00:00Z")
    assert row["end"] == pd.Timestamp("2024-01-19T11:00:00Z")
    assert str(processed.encounters["start"].dt.tz) == "UTC"
    assert str(processed.encounters["end"].dt.tz) == "UTC"


def test_process_keeps_missing_encounter_end_empty():
    encounter = make_encounter(period={"start": "2024-06-03T14:30:00+02:00"})
    frames = bundle_to_frames(make_bundle(PATIENT, encounter))

    processed = process(frames)

    assert pd.isna(processed.encounters.iloc[0]["end"])


def test_process_parses_birth_date():
    patient = {"resourceType": "Patient", "id": "p1", "birthDate": "2001-07-02"}
    frames = bundle_to_frames(make_bundle(patient))

    processed = process(frames)

    row = processed.patients.iloc[0]
    assert row["birth_date"] == pd.Timestamp("2001-07-02")
    assert processed.patients["birth_date"].dt.tz is None


def test_process_keeps_missing_birth_date_empty():
    frames = bundle_to_frames(make_bundle(PATIENT))

    processed = process(frames)

    row = processed.patients.iloc[0]
    assert pd.isna(row["birth_date"])


def test_process_does_not_modify_input_frames():
    frames = bundle_to_frames(make_bundle(PATIENT, ENCOUNTER, make_observation()))

    process(frames)

    assert frames.observations.iloc[0]["start"] == "2024-01-15T09:00:00+01:00"


def test_process_converts_procedure_times_to_utc():
    frames = bundle_to_frames(make_bundle(PATIENT, ENCOUNTER, make_procedure()))

    processed = process(frames)

    row = processed.procedures.iloc[0]
    assert row["start"] == pd.Timestamp("2024-01-15T09:00:00Z")
    assert pd.isna(row["end"])
    assert str(processed.procedures["start"].dt.tz) == "UTC"
