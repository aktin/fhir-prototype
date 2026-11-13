import copy

import pandas as pd
import pytest

from fhir_prototype.bundle_index import BundleIndex, UnresolvedReferenceError
from fhir_prototype.bundle_loader import load_bundle
from fhir_prototype.facts import (
    FACT_COLUMNS,
    _device_category,
    _first,
    _profile,
    _row,
    _split,
    build_facts,
)
from fhir_prototype.mapping import load_mapping
from helpers import (
    BASE,
    ENCOUNTER,
    FIXTURES,
    PATIENT,
    make_bundle,
    make_observation,
    make_procedure,
)

START = "effectivePeriod.start | effectiveDateTime"


def test_first_returns_value_at_path():
    observation = make_observation()

    assert _first(observation, "valueQuantity.value") == 80
    assert _first(observation, "valueQuantity.code") == "/min"


def test_first_returns_none_without_path_or_match():
    observation = make_observation()

    assert _first(observation, None) is None
    assert _first(observation, "") is None
    assert _first(observation, "valueInteger") is None


def test_first_reads_start_from_datetime_or_period():
    with_datetime = make_observation()
    with_period = make_observation(effectivePeriod={
        "start": "2024-01-15T10:00:00+01:00",
        "end": "2024-01-15T10:01:00+01:00",
    })
    del with_period["effectiveDateTime"]

    assert _first(with_datetime, START) == "2024-01-15T09:00:00+01:00"
    assert _first(with_period, START) == "2024-01-15T10:00:00+01:00"


def test_first_does_not_modify_resource():
    observation = make_observation()
    before = copy.deepcopy(observation)

    _first(observation, "valueQuantity.value")

    assert observation == before


@pytest.mark.parametrize("fixture", [
    "bundle_min.json",
    "bundle_max_1.json",
    "bundle_max_2.json",
])
def test_fhirpath_expressions_evaluate_on_fixtures(fixture):
    index = BundleIndex(load_bundle(FIXTURES / fixture))

    for observation in index.of_type("Observation"):
        assert _first(observation, START) is not None
        values = [
            _first(observation, "valueQuantity.value"),
            _first(observation, "valueInteger"),
            _first(observation, "valueCodeableConcept.text"),
        ]
        assert sum(value is not None for value in values) == 1

    for procedure in index.of_type("Procedure"):
        assert _first(procedure, "performedPeriod.start | performedDateTime") is not None


RULE = {
    "profile": "https://example.org/StructureDefinition/heartrate",
    "device_category": None,
    "concept_cd": "LOINC:8867-4",
    "valtype_cd": "N",
    "value": "valueQuantity.value",
    "unit": "valueQuantity.code",
    "start": "effectivePeriod.start | effectiveDateTime",
    "end": "effectivePeriod.end",
    "expected_unit": "/min",
}


def test_row_translates_observation_by_rule():
    observation = make_observation()
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, observation))

    row = _row(observation, index, RULE)

    assert row == {
        "resource_type": "Observation",
        "resource_id": "o1",
        "patient_id": "p1",
        "encounter_id": "e1",
        "concept_cd": "LOINC:8867-4",
        "modifier_cd": "@",
        "start_date": "2024-01-15T09:00:00+01:00",
        "end_date": None,
        "valtype_cd": "N",
        "tval_char": None,
        "alt_codes": [],
        "nval_num": 80,
        "units_cd": "/min",
        "expected_unit": "/min",
    }


def test_row_reads_period_of_observation():
    observation = make_observation(effectivePeriod={
        "start": "2024-01-15T10:00:00+01:00",
        "end": "2024-01-15T10:01:00+01:00",
    })
    del observation["effectiveDateTime"]
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, observation))

    row = _row(observation, index, RULE)

    assert row["start_date"] == "2024-01-15T10:00:00+01:00"
    assert row["end_date"] == "2024-01-15T10:01:00+01:00"


def test_row_translates_procedure_without_value():
    procedure = make_procedure()
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, procedure))
    rule = {
        "concept_cd": "SNOMED:1149092001",
        "start": "performedPeriod.start | performedDateTime",
        "end": "performedPeriod.end",
    }

    row = _row(procedure, index, rule)

    assert row["resource_type"] == "Procedure"
    assert row["resource_id"] == "pr1"
    assert row["concept_cd"] == "SNOMED:1149092001"
    assert row["start_date"] == "2024-01-15T10:00:00+01:00"
    assert row["end_date"] is None
    assert row["valtype_cd"] is None
    assert row["nval_num"] is None
    assert row["units_cd"] is None


def test_row_without_rule_keeps_identity_but_has_no_concept():
    observation = make_observation()
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, observation))

    row = _row(observation, index, {})

    assert row["resource_id"] == "o1"
    assert row["patient_id"] == "p1"
    assert row["encounter_id"] == "e1"
    assert row["concept_cd"] is None
    assert row["nval_num"] is None
    assert row["start_date"] is None


def make_fact(**overrides):
    fact = {
        "resource_type": "Observation",
        "resource_id": "o1",
        "patient_id": "p1",
        "encounter_id": "e1",
        "concept_cd": "LOINC:8867-4",
        "modifier_cd": "@",
        "start_date": "2024-01-15T09:00:00+01:00",
        "end_date": None,
        "valtype_cd": "N",
        "tval_char": None,
        "alt_codes": [],
        "nval_num": 80,
        "units_cd": "/min",
        "expected_unit": "/min",
    }
    fact.update(overrides)
    return fact


def test_split_accepts_complete_fact():
    result = _split(pd.DataFrame([make_fact()]))

    assert len(result.facts) == 1
    assert len(result.unmapped) == 0
    assert list(result.facts.columns) == FACT_COLUMNS
    assert list(result.unmapped.columns) == FACT_COLUMNS + ["reason"]


def test_split_rejects_fact_without_concept():
    result = _split(pd.DataFrame([make_fact(concept_cd=None)]))

    assert len(result.facts) == 0
    assert result.unmapped["reason"].tolist() == ["no concept in mapping"]


def test_split_rejects_numeric_fact_without_value():
    result = _split(pd.DataFrame([make_fact(nval_num=None)]))

    assert len(result.facts) == 0
    assert result.unmapped["reason"].tolist() == ["no numeric value"]


def test_split_rejects_fact_with_unexpected_unit():
    result = _split(pd.DataFrame([make_fact(units_cd="/h")]))

    assert len(result.facts) == 0
    assert result.unmapped["reason"].tolist() == ["unit differs from expected_unit"]


def test_split_accepts_fact_without_expected_unit():
    result = _split(pd.DataFrame([make_fact(units_cd="mm[Hg]", expected_unit=None)]))

    assert len(result.facts) == 1


def test_split_accepts_fact_without_value_type():
    procedure = make_fact(resource_type="Procedure", valtype_cd=None, nval_num=None, units_cd=None, expected_unit=None)

    result = _split(pd.DataFrame([procedure]))

    assert len(result.facts) == 1


def test_split_names_missing_concept_before_other_reasons():
    result = _split(pd.DataFrame([make_fact(concept_cd=None, nval_num=None, units_cd="/h")]))

    assert result.unmapped["reason"].tolist() == ["no concept in mapping"]


def test_split_separates_accepted_and_rejected_rows():
    facts = pd.DataFrame([
        make_fact(resource_id="o1"),
        make_fact(resource_id="o2", concept_cd=None),
        make_fact(resource_id="o3", nval_num=None),
    ])

    result = _split(facts)

    assert result.facts["resource_id"].tolist() == ["o1"]
    assert result.unmapped["resource_id"].tolist() == ["o2", "o3"]
    assert result.unmapped["reason"].tolist() == ["no concept in mapping", "no numeric value"]


PROCEDURE_RULE = {
    "profile": "https://example.org/StructureDefinition/ventilation",
    "device_category": None,
    "concept_cd": "SNOMED:1149092001",
    "valtype_cd": None,
    "start": "performedPeriod.start | performedDateTime",
    "end": "performedPeriod.end",
}


def facts_of(*resources, rules=(RULE, PROCEDURE_RULE)):
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, *resources))
    return build_facts(index, list(rules))


def test_build_facts_translates_observations_and_procedures():
    result = facts_of(make_observation(), make_procedure())

    assert result.facts["resource_type"].tolist() == ["Observation", "Procedure"]
    assert result.facts["concept_cd"].tolist() == ["LOINC:8867-4", "SNOMED:1149092001"]
    assert len(result.unmapped) == 0


def test_build_facts_returns_fact_columns_with_tval_char():
    result = facts_of(make_observation())

    assert list(result.facts.columns) == FACT_COLUMNS
    assert FACT_COLUMNS.index("tval_char") == FACT_COLUMNS.index("valtype_cd") + 1


def test_build_facts_converts_times_to_utc():
    result = facts_of(make_observation())

    assert result.facts.iloc[0]["start_date"] == pd.Timestamp("2024-01-15T08:00:00Z")
    assert str(result.facts["start_date"].dt.tz) == "UTC"
    assert pd.isna(result.facts.iloc[0]["end_date"])


def test_build_facts_stores_decimal_value_as_number():
    rule = {**RULE, "expected_unit": "Cel"}
    observation = make_observation(valueQuantity={"value": 36.6, "unit": "°C", "code": "Cel"})

    result = facts_of(observation, rules=[rule])

    assert result.facts.iloc[0]["nval_num"] == 36.6
    assert result.facts["nval_num"].dtype == "float64"


def test_build_facts_reads_number_from_text():
    rule = {**RULE, "value": "valueCodeableConcept.text", "unit": None, "expected_unit": None}
    observation = make_observation(valueCodeableConcept={"text": "-4"})
    del observation["valueQuantity"]

    result = facts_of(observation, rules=[rule])

    assert result.facts.iloc[0]["nval_num"] == -4


def test_build_facts_rejects_text_that_is_not_a_number():
    rule = {**RULE, "value": "valueCodeableConcept.text", "unit": None, "expected_unit": None}
    observation = make_observation(valueCodeableConcept={"text": "unknown"})
    del observation["valueQuantity"]

    result = facts_of(observation, rules=[rule])

    assert len(result.facts) == 0
    assert result.unmapped["reason"].tolist() == ["no numeric value"]


def test_build_facts_leaves_value_empty_without_numeric_value_type():
    result = facts_of(make_procedure())

    assert pd.isna(result.facts.iloc[0]["nval_num"])
    assert pd.isna(result.facts.iloc[0]["valtype_cd"])


def test_build_facts_moves_resource_without_rule_to_unmapped():
    result = facts_of(make_observation(), rules=[])

    assert len(result.facts) == 0
    assert result.unmapped["resource_id"].tolist() == ["o1"]
    assert result.unmapped["reason"].tolist() == ["no concept in mapping"]


def test_build_facts_skips_resources_with_excluded_status():
    result = facts_of(
        make_observation(),
        make_observation(id="o2", status="entered-in-error"),
        make_observation(id="o3", status="cancelled"),
    )

    assert result.facts["resource_id"].tolist() == ["o1"]
    assert len(result.unmapped) == 0


def test_build_facts_picks_rule_by_device_category():
    device = {"resourceType": "DeviceMetric", "id": "d1", "category": "setting"}
    observation = make_observation(device={"reference": f"{BASE}/DeviceMetric/d1"})
    rules = [
        {**RULE, "device_category": "setting", "concept_cd": "TEST:SET"},
        {**RULE, "device_category": "measurement", "concept_cd": "TEST:MEAS"},
    ]

    result = facts_of(device, observation, rules=rules)

    assert result.facts["concept_cd"].tolist() == ["TEST:SET"]


def test_build_facts_handles_bundle_without_fact_resources():
    result = facts_of()

    assert len(result.facts) == 0
    assert len(result.unmapped) == 0
    assert list(result.facts.columns) == FACT_COLUMNS


@pytest.mark.parametrize("fixture, facts, unmapped", [
    ("bundle_min.json", 51, 10),
    ("bundle_max_1.json", 201, 40),
    ("bundle_max_2.json", 201, 40),
])
def test_build_facts_counts_in_fixtures(fixture, facts, unmapped):
    index = BundleIndex(load_bundle(FIXTURES / fixture))

    result = build_facts(index, load_mapping())

    assert len(result.facts) == facts
    assert len(result.unmapped) == unmapped
    assert set(result.unmapped["reason"]) == {"no concept in mapping"}
    assert result.facts["concept_cd"].notna().all()
    assert result.facts["start_date"].notna().all()


def test_build_facts_handles_dst_change_in_max_bundle_2():
    index = BundleIndex(load_bundle(FIXTURES / "bundle_max_2.json"))

    result = build_facts(index, load_mapping())

    def start_of(table, resource_id):
        return table[table["resource_id"] == resource_id].iloc[0]["start_date"]

    assert str(result.facts["start_date"].dt.tz) == "UTC"
    assert start_of(result.facts, "icu-rass-a6170189a93b") == pd.Timestamp("2024-03-31T08:00:00Z")
    assert start_of(result.unmapped, "icu-vent-map-measured-bd30493bd56f") == pd.Timestamp("2024-03-31T00:29:00Z")


ALT_RULE = {**RULE, "alt_codes": ["LOINC:8310-5", "SNOMED:386725007"]}


def test_build_facts_adds_alt_code_row_per_alternative_code():
    result = facts_of(make_observation(), rules=[ALT_RULE])

    facts = result.facts
    assert facts["modifier_cd"].tolist() == ["@", "altCode", "altCode"]
    assert facts["valtype_cd"].tolist() == ["N", "T", "T"]
    assert facts["tval_char"].tolist()[1:] == ["LOINC:8310-5", "SNOMED:386725007"]
    assert pd.isna(facts["tval_char"].iloc[0])
    assert facts["concept_cd"].tolist() == ["LOINC:8867-4"] * 3
    assert facts["resource_id"].tolist() == ["o1"] * 3
    assert facts["start_date"].nunique() == 1
    assert facts["nval_num"].iloc[0] == 80
    assert facts["nval_num"].iloc[1:].isna().all()
    assert facts["units_cd"].iloc[1:].isna().all()


def test_build_facts_adds_no_alt_code_rows_for_rejected_fact():
    observation = make_observation(valueQuantity={"value": 80, "unit": "/h", "code": "/h"})

    result = facts_of(observation, rules=[ALT_RULE])

    assert len(result.facts) == 0
    assert len(result.unmapped) == 1


def test_build_facts_adds_no_alt_code_rows_without_alternative_codes():
    result = facts_of(make_observation())

    assert result.facts["modifier_cd"].tolist() == ["@"]


def test_profile_returns_first_profile_of_resource():
    assert _profile(make_observation()) == "https://example.org/StructureDefinition/heartrate"


def test_profile_is_none_without_meta():
    observation = make_observation()
    del observation["meta"]

    assert _profile(observation) is None


def test_device_category_reads_category_of_referenced_device():
    device = {"resourceType": "DeviceMetric", "id": "d1", "category": "measurement"}
    observation = make_observation(device={"reference": f"{BASE}/DeviceMetric/d1"})
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, device, observation))

    assert _device_category(observation, index) == "measurement"


def test_device_category_is_none_without_device():
    observation = make_observation()
    index = BundleIndex(make_bundle(PATIENT, ENCOUNTER, observation))

    assert _device_category(observation, index) is None


@pytest.mark.parametrize("field", ["subject", "encounter", "device"])
def test_build_facts_fails_on_unknown_reference(field):
    missing = f"{BASE}/Unknown/does-not-exist"
    observation = make_observation(**{field: {"reference": missing}})

    with pytest.raises(UnresolvedReferenceError, match=missing):
        facts_of(observation)
