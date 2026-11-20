import json

import pandas as pd
import pytest

from fhir_prototype.bundle_loader import InvalidBundleError
from fhir_prototype.importer import CsvImporter, Importer
from fhir_prototype.pipeline import run
from fhir_prototype.validation import BundleValidator
from helpers import BASE, FIXTURES, PATIENT, make_bundle, make_encounter, make_observation, write_zip

FIXTURE_NAMES = ["bundle_min.json", "bundle_max_1.json", "bundle_max_2.json"]


class RecordingImporter(Importer):
    def __init__(self):
        self.calls = []

    def write(self, name, frames, result):
        self.calls.append((name, frames, result))


class RecordingValidator(BundleValidator):
    def __init__(self):
        self.seen = []

    def is_valid(self, bundle):
        self.seen.append(bundle)
        return True


class RejectAll(BundleValidator):
    def is_valid(self, bundle):
        return False


def _fixture_zip(tmp_path):
    entries = {name: (FIXTURES / name).read_text(encoding="utf-8") for name in FIXTURE_NAMES}
    return write_zip(tmp_path / "delivery.zip", entries)


def test_run_hands_every_bundle_to_importer(tmp_path):
    importer = RecordingImporter()

    run(_fixture_zip(tmp_path), importer)

    assert [name for name, _, _ in importer.calls] == sorted(FIXTURE_NAMES)


def test_run_writes_one_subfolder_per_bundle(tmp_path):
    output = tmp_path / "output"

    run(_fixture_zip(tmp_path), CsvImporter(output))

    for name in FIXTURE_NAMES:
        for file in ["patients.csv", "encounters.csv", "facts.csv", "unmapped.csv"]:
            assert (output / name.removesuffix(".json") / file).exists()
    facts = pd.read_csv(output / "bundle_min" / "facts.csv")
    assert len(facts) == 51
    assert facts["concept_cd"].notna().all()


def test_run_skips_bundle_with_unresolved_reference(tmp_path, caplog):
    broken = make_bundle(
        PATIENT,
        make_encounter(subject={"reference": f"{BASE}/Patient/missing"}),
        make_observation(encounter={"reference": f"{BASE}/Encounter/missing"}),
    )
    path = write_zip(
        tmp_path / "delivery.zip",
        {
            "broken.json": json.dumps(broken),
            "bundle_min.json": (FIXTURES / "bundle_min.json").read_text(encoding="utf-8"),
        },
    )
    importer = RecordingImporter()

    run(path, importer)

    assert [name for name, _, _ in importer.calls] == ["bundle_min.json"]
    assert len(caplog.records) == 1
    assert "broken.json" in caplog.records[0].getMessage()


def test_run_calls_validator_for_every_bundle(tmp_path):
    validator = RecordingValidator()

    run(_fixture_zip(tmp_path), RecordingImporter(), validator=validator)

    assert len(validator.seen) == 3


def test_run_fails_when_no_bundle_could_be_processed(tmp_path, caplog):
    importer = RecordingImporter()

    with pytest.raises(InvalidBundleError, match="no bundle could be processed"):
        run(_fixture_zip(tmp_path), importer, validator=RejectAll())

    assert importer.calls == []
    assert len(caplog.records) == 3
