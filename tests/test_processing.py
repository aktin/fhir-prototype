import pandas as pd

from fhir_prototype.bundle_index import BundleIndex
from fhir_prototype.frames import bundle_to_frames
from fhir_prototype.processing import process
from helpers import ENCOUNTER, PATIENT, make_bundle, make_observation, FIXTURES
from fhir_prototype.bundle_loader import load_bundle

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