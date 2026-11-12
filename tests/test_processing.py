import pandas as pd
from helpers import PATIENT, make_bundle, make_encounter

from fhir_prototype.bundle_index import BundleIndex
from fhir_prototype.frames import bundle_to_frames
from fhir_prototype.processing import process, to_datetime


def frames_of(*resources):
    return bundle_to_frames(BundleIndex(make_bundle(*resources)))


def test_process_converts_encounter_times_to_utc():
    frames = frames_of(PATIENT, make_encounter())

    processed = process(frames)

    row = processed.encounters.iloc[0]
    assert row["start"] == pd.Timestamp("2024-01-15T08:00:00Z")
    assert row["end"] == pd.Timestamp("2024-01-19T11:00:00Z")
    assert str(processed.encounters["start"].dt.tz) == "UTC"
    assert str(processed.encounters["end"].dt.tz) == "UTC"


def test_process_keeps_missing_encounter_end_empty():
    encounter = make_encounter(period={"start": "2024-06-03T14:30:00+02:00"})
    frames = frames_of(PATIENT, encounter)

    processed = process(frames)

    assert pd.isna(processed.encounters.iloc[0]["end"])


def test_process_parses_birth_date():
    patient = {"resourceType": "Patient", "id": "p1", "birthDate": "2001-07-02"}
    frames = frames_of(patient)

    processed = process(frames)

    row = processed.patients.iloc[0]
    assert row["birth_date"] == pd.Timestamp("2001-07-02")
    assert processed.patients["birth_date"].dt.tz is None


def test_process_keeps_missing_birth_date_empty():
    frames = frames_of(PATIENT)

    processed = process(frames)

    row = processed.patients.iloc[0]
    assert pd.isna(row["birth_date"])


def test_process_does_not_modify_input_frames():
    frames = frames_of(PATIENT, make_encounter())

    process(frames)

    assert frames.encounters.iloc[0]["start"] == "2024-01-15T09:00:00+01:00"


def test_to_datetime_converts_to_utc_by_default():
    df = pd.DataFrame({"start": ["2024-01-15T09:00:00+01:00", None]})

    result = to_datetime(df, ["start"])

    assert result.iloc[0]["start"] == pd.Timestamp("2024-01-15T08:00:00Z")
    assert pd.isna(result.iloc[1]["start"])
    assert str(result["start"].dt.tz) == "UTC"


def test_to_datetime_handles_mixed_offsets():
    df = pd.DataFrame({"start": ["2024-03-30T23:00:00+01:00", "2024-03-31T09:00:00+02:00"]})

    result = to_datetime(df, ["start"])

    assert result["start"].tolist() == [
        pd.Timestamp("2024-03-30T22:00:00Z"),
        pd.Timestamp("2024-03-31T07:00:00Z"),
    ]


def test_to_datetime_keeps_values_naive_without_utc():
    df = pd.DataFrame({"birth_date": ["2001-07-02"]})

    result = to_datetime(df, ["birth_date"], utc=False)

    assert result.iloc[0]["birth_date"] == pd.Timestamp("2001-07-02")
    assert result["birth_date"].dt.tz is None


def test_to_datetime_does_not_modify_input():
    df = pd.DataFrame({"start": ["2024-01-15T09:00:00+01:00"]})

    to_datetime(df, ["start"])

    assert df.iloc[0]["start"] == "2024-01-15T09:00:00+01:00"
