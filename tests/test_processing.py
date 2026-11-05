import pandas as pd

from fhir_prototype.frames import bundle_to_frames
from fhir_prototype.processing import process
from helpers import ENCOUNTER, PATIENT, make_bundle, make_observation


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
