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
