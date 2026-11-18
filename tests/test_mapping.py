import pytest

from fhir_prototype.bundle_index import BundleIndex
from fhir_prototype.bundle_loader import load_bundle
from fhir_prototype.facts import _first, _profile
from fhir_prototype.mapping import load_mapping
from helpers import FIXTURES

FIXTURE_NAMES = ["bundle_min.json", "bundle_max_1.json", "bundle_max_2.json"]
RASS_PROFILE = "https://www.medizininformatik-initiative.de/fhir/ext/modul-icu/StructureDefinition/mii-pr-icu-score-rass"


def expressions(rule):
    """Return every @ expression of a rule, without the @."""
    parts = [rule["concept"], *rule.get("modifiers", {}).values()]
    return [
        value[1:]
        for part in parts
        for value in part.values()
        if isinstance(value, str) and value.startswith("@")
    ]


def test_load_mapping_returns_rules_keyed_by_profile():
    mapping = load_mapping()

    assert isinstance(mapping, dict)
    assert list(mapping) == [RASS_PROFILE]


def test_every_rule_has_a_concept_with_code_and_start():
    for rule in load_mapping().values():
        assert set(rule) <= {"concept", "modifiers"}
        assert rule["concept"]["concept_cd"]
        assert rule["concept"]["start_date"].startswith("@")


def test_modifiers_never_use_the_main_fact_modifier():
    for rule in load_mapping().values():
        assert "@" not in rule.get("modifiers", {})


@pytest.mark.parametrize("fixture", FIXTURE_NAMES)
def test_rule_expressions_evaluate_on_matching_resources_in_fixtures(fixture):
    index = BundleIndex(load_bundle(FIXTURES / fixture))
    mapping = load_mapping()
    matching = [
        (resource, mapping[_profile(resource)])
        for resource in index.of_type("Observation") + index.of_type("Procedure")
        if _profile(resource) in mapping
    ]

    assert matching
    for resource, rule in matching:
        for expression in expressions(rule):
            _first(resource, expression)
        assert _first(resource, rule["concept"]["start_date"][1:]) is not None
        if rule["concept"].get("valtype_cd") == "N":
            assert _first(resource, rule["concept"]["nval_num"][1:]) is not None