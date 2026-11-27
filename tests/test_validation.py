import json
import logging
import subprocess
import sys
from pathlib import Path

import pytest

from fhir_prototype.validation import HapiValidator, outcome_is_valid, select_resources
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


class FakeValidatorRun:
    """Stands in for subprocess.run: records the command and writes the given OperationOutcome."""

    def __init__(self, outcome, returncode=0):
        self.outcome = outcome
        self.returncode = returncode
        self.command = None
        self.bundle = None

    def __call__(self, command, **kwargs):
        self.command = [str(part) for part in command]
        self.bundle = json.loads(Path(self.command[4]).read_text(encoding="utf-8"))
        if self.outcome is not None:
            output = Path(self.command[self.command.index("-output") + 1])
            output.write_text(json.dumps(self.outcome), encoding="utf-8")
        return subprocess.CompletedProcess(command, self.returncode, stdout="", stderr="java.lang.OutOfMemoryError")


@pytest.fixture
def make_validator(tmp_path, monkeypatch):
    def make(outcome, returncode=0):
        fake = FakeValidatorRun(outcome, returncode)
        monkeypatch.setattr(subprocess, "run", fake)
        jar = tmp_path / "validator_cli.jar"
        jar.touch()
        validator = HapiValidator(
            profiles={MAPPED},
            java=sys.executable,
            jar=jar,
            ig=tmp_path / "profiles",
            fhir_home=tmp_path / "fhir-home",
        )
        return validator, fake

    return make


def test_hapi_validator_without_issues_is_valid(make_validator):
    validator, _ = make_validator(_outcome())

    assert validator.is_valid(make_bundle(PATIENT))


def test_hapi_validator_with_only_warnings_is_valid(make_validator):
    validator, _ = make_validator(_outcome(_issue("warning", "unknown code")))

    assert validator.is_valid(make_bundle(PATIENT))


def test_hapi_validator_with_error_is_invalid(make_validator):
    validator, _ = make_validator(_outcome(_issue("error", "slice not found")), returncode=1)

    assert not validator.is_valid(make_bundle(PATIENT))


def test_hapi_validator_calls_validator_for_r4_offline(make_validator, tmp_path):
    validator, fake = make_validator(_outcome())

    validator.is_valid(make_bundle(PATIENT))

    assert fake.command[:4] == [
        sys.executable,
        f"-Duser.home={tmp_path / 'fhir-home'}",
        "-jar",
        str(tmp_path / "validator_cli.jar"),
    ]
    options = fake.command[5:]
    assert options[options.index("-version") + 1] == "4.0.1"
    assert options[options.index("-ig") + 1] == str(tmp_path / "profiles")
    assert options[options.index("-tx") + 1] == "n/a"


def test_hapi_validator_passes_only_selected_resources(make_validator, caplog):
    caplog.set_level(logging.INFO, logger="fhir_prototype.validation")
    validator, fake = make_validator(_outcome())
    other = make_observation(id="o2", meta={"profile": [OTHER]})

    validator.is_valid(make_bundle(PATIENT, ENCOUNTER, make_observation(id="o1"), other))

    assert _types_and_ids(fake.bundle) == [("Patient", "p1"), ("Encounter", "e1"), ("Observation", "o1")]
    assert "Ignored 1 resources with a profile outside the mapping" in caplog.messages


def test_hapi_validator_raises_if_validator_writes_no_outcome(make_validator):
    validator, _ = make_validator(None, returncode=2)

    with pytest.raises(RuntimeError, match="OutOfMemoryError"):
        validator.is_valid(make_bundle(PATIENT))


def test_hapi_validator_raises_if_java_is_missing(tmp_path):
    jar = tmp_path / "validator_cli.jar"
    jar.touch()

    with pytest.raises(FileNotFoundError, match="no-such-java"):
        HapiValidator(profiles=set(), java="no-such-java", jar=jar, ig=tmp_path, fhir_home=tmp_path)


def test_hapi_validator_raises_if_jar_is_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match="validator_cli.jar"):
        HapiValidator(
            profiles=set(), java=sys.executable, jar=tmp_path / "validator_cli.jar", ig=tmp_path, fhir_home=tmp_path
        )
