import pandas as pd

from fhir_prototype.facts import observation_facts
from fhir_prototype.frames import bundle_to_frames
from fhir_prototype.mapping import load_mapping
from fhir_prototype.processing import process
from helpers import ENCOUNTER, PATIENT, make_bundle, make_observation

HEART_RATE_PROFILE = (
    "https://www.medizininformatik-initiative.de/fhir/ext/modul-icu/"
    "StructureDefinition/mii-pr-icu-muv-herzfrequenz"
)

RASS_PROFILE = (
    "https://www.medizininformatik-initiative.de/fhir/ext/modul-icu/"
    "StructureDefinition/mii-pr-icu-score-rass"
)


def test_observation_facts_assigns_concept_from_mapping():
    observation = make_observation(meta={"profile": [HEART_RATE_PROFILE]})
    frames = process(bundle_to_frames(make_bundle(PATIENT, ENCOUNTER, observation)))

    facts = observation_facts(frames.observations, load_mapping())

    assert len(facts) == 1
    assert facts.iloc[0]["concept_cd"] == "LOINC:8867-4"


def test_observation_facts_keeps_unmapped_observation_with_empty_concept():
    frames = process(bundle_to_frames(make_bundle(PATIENT, ENCOUNTER, make_observation())))

    facts = observation_facts(frames.observations, load_mapping())

    assert len(facts) == 1
    assert pd.isna(facts.iloc[0]["concept_cd"])


def test_observation_facts_puts_numeric_value_into_nval_num():
    observation = make_observation(meta={"profile": [HEART_RATE_PROFILE]})
    frames = process(bundle_to_frames(make_bundle(PATIENT, ENCOUNTER, observation)))

    facts = observation_facts(frames.observations, load_mapping())

    row = facts.iloc[0]
    assert row["valtype_cd"] == "N"
    assert row["nval_num"] == 80
    assert row["units_cd"] == "/min"


def test_observation_facts_reads_rass_score_from_value_text():
    observation = make_observation(
        meta={"profile": [RASS_PROFILE]},
        valueCodeableConcept={
            "coding": [{"system": "http://loinc.org", "code": "LA33966-5"}],
            "text": "-4",
        },
    )
    del observation["valueQuantity"]
    frames = process(bundle_to_frames(make_bundle(PATIENT, ENCOUNTER, observation)))

    facts = observation_facts(frames.observations, load_mapping())

    assert facts.iloc[0]["nval_num"] == -4


def test_observation_facts_has_fact_columns():
    observation = make_observation(meta={"profile": [HEART_RATE_PROFILE]})
    frames = process(bundle_to_frames(make_bundle(PATIENT, ENCOUNTER, observation)))

    facts = observation_facts(frames.observations, load_mapping())

    assert list(facts.columns) == [
        "observation_id",
        "patient_id",
        "encounter_id",
        "concept_cd",
        "modifier_cd",
        "start_date",
        "end_date",
        "valtype_cd",
        "nval_num",
        "units_cd",
    ]
    row = facts.iloc[0]
    assert row["modifier_cd"] == "@"
    assert row["start_date"] == pd.Timestamp("2024-01-15T08:00:00Z")
