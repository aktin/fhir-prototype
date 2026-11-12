import pytest
from helpers import FIXTURES

from fhir_prototype.bundle_index import BundleIndex
from fhir_prototype.bundle_loader import load_bundle
from fhir_prototype.facts import _device_category, _first, _profile
from fhir_prototype.mapping import load_mapping

FIXTURE_NAMES = ["bundle_min.json", "bundle_max_1.json", "bundle_max_2.json"]
RULE_KEYS = [
    "profile",
    "device_category",
    "concept_cd",
    "valtype_cd",
    "value",
    "unit",
    "start",
    "end",
    "expected_unit",
    "status",
    "open_question",
    "note",
]


def rules_by_key():
    return {(rule["profile"], rule["device_category"]): rule for rule in load_mapping()}


def fact_resources(index):
    return index.of_type("Observation") + index.of_type("Procedure")


def test_load_mapping_returns_rules_with_expected_keys():
    mapping = load_mapping()

    assert len(mapping) == 31
    for rule in mapping:
        assert list(rule) == RULE_KEYS


def test_mapping_has_unique_profile_and_device_category():
    mapping = load_mapping()

    assert len(rules_by_key()) == len(mapping)


def test_mapping_keeps_rules_without_concept():
    assert any(rule["concept_cd"] is None for rule in load_mapping())


@pytest.mark.parametrize("fixture", FIXTURE_NAMES)
def test_mapping_covers_all_fact_resources_in_fixtures(fixture):
    index = BundleIndex(load_bundle(FIXTURES / fixture))
    rules = rules_by_key()

    for resource in fact_resources(index):
        assert (_profile(resource), _device_category(resource, index)) in rules


@pytest.mark.parametrize("fixture", FIXTURE_NAMES)
def test_mapping_expressions_find_start_and_value_in_fixtures(fixture):
    index = BundleIndex(load_bundle(FIXTURES / fixture))
    rules = rules_by_key()

    for resource in fact_resources(index):
        rule = rules[(_profile(resource), _device_category(resource, index))]
        assert _first(resource, rule["start"]) is not None
        if rule["valtype_cd"] == "N":
            assert _first(resource, rule["value"]) is not None
