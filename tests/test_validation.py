import logging

from fhir_prototype.validation import outcome_is_valid, select_resources
from helpers import ENCOUNTER, PATIENT, make_bundle, make_observation

MAPPED = "https://example.org/StructureDefinition/heartrate"
OTHER = "https://pdms.example.org/StructureDefinition/vendor-specific"


def _types_and_ids(bundle):
    return [(entry["resource"]["resourceType"], entry["resource"]["id"]) for entry in bundle["entry"]]


def test_select_resources_keeps_patient_encounter_and_mapped_profiles():
    bundle = make_bundle(PATIENT, ENCOUNTER, make_observation(id="o1"))

    selected, ignored = select_resources(bundle, {MAPPED})

    assert _types_and_ids(selected) == [("Patient", "p1"), ("Encounter", "e1"), ("Observation", "o1")]
    assert ignored == 0


def test_select_resources_drops_resources_with_other_profiles():
    other = make_observation(id="o2", meta={"profile": [OTHER]})
    bundle = make_bundle(PATIENT, make_observation(id="o1"), other)

    selected, ignored = select_resources(bundle, {MAPPED})

    assert _types_and_ids(selected) == [("Patient", "p1"), ("Observation", "o1")]
    assert ignored == 1


def test_select_resources_drops_resources_without_profile():
    bundle = make_bundle(make_observation(id="o1", meta={}))

    selected, ignored = select_resources(bundle, {MAPPED})

    assert selected["entry"] == []
    assert ignored == 1


def test_select_resources_keeps_resource_if_any_profile_is_mapped():
    both = make_observation(id="o1", meta={"profile": [OTHER, MAPPED]})

    selected, _ = select_resources(make_bundle(both), {MAPPED})

    assert _types_and_ids(selected) == [("Observation", "o1")]


def test_select_resources_does_not_change_the_input_bundle():
    bundle = make_bundle(make_observation(id="o2", meta={"profile": [OTHER]}))

    select_resources(bundle, {MAPPED})

    assert len(bundle["entry"]) == 1


def _issue(severity, text, expression="Bundle.entry[0].resource"):
    return {"severity": severity, "code": "processing", "details": {"text": text}, "expression": [expression]}


def _outcome(*issues):
    return {"resourceType": "OperationOutcome", "issue": list(issues)}


def test_outcome_without_issues_is_valid():
    assert outcome_is_valid({"resourceType": "OperationOutcome"})


def test_outcome_with_only_warnings_and_information_is_valid(caplog):
    outcome = _outcome(_issue("warning", "unknown code"), _issue("information", "no terminology server"))

    assert outcome_is_valid(outcome)
    assert [(r.levelno, r.getMessage()) for r in caplog.records] == [
        (logging.WARNING, "Bundle.entry[0].resource: unknown code")
    ]


def test_outcome_with_error_is_invalid(caplog):
    outcome = _outcome(_issue("warning", "unknown code"), _issue("error", "slice not found"))

    assert not outcome_is_valid(outcome)
    assert (logging.ERROR, "Bundle.entry[0].resource: slice not found") in [
        (r.levelno, r.getMessage()) for r in caplog.records
    ]


def test_outcome_with_fatal_is_invalid():
    assert not outcome_is_valid(_outcome(_issue("fatal", "cannot parse")))


def test_outcome_issue_without_expression_is_logged(caplog):
    outcome = _outcome({"severity": "error", "code": "processing", "details": {"text": "no profile"}})

    assert not outcome_is_valid(outcome)
    assert [r.getMessage() for r in caplog.records] == ["no profile"]
