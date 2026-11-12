import pandas as pd
import pytest
from helpers import FIXTURES

from fhir_prototype.bundle_loader import InvalidBundleError
from fhir_prototype.importer import CsvImporter, Importer
from fhir_prototype.pipeline import run
from fhir_prototype.validation import BundleValidator


class RecordingImporter(Importer):
    def __init__(self):
        self.calls = []

    def write(self, frames, result):
        self.calls.append((frames, result))


class RejectAll(BundleValidator):
    def is_valid(self, bundle):
        return False


def test_run_hands_frames_and_result_to_importer():
    importer = RecordingImporter()

    result = run(FIXTURES / "bundle_min.json", importer)

    assert len(importer.calls) == 1
    frames, written = importer.calls[0]
    assert written is result
    assert len(frames.patients) == 1
    assert len(frames.encounters) == 1


def test_run_writes_facts_and_unmapped_csv(tmp_path):
    run(FIXTURES / "bundle_min.json", CsvImporter(tmp_path))

    facts = pd.read_csv(tmp_path / "facts.csv")
    unmapped = pd.read_csv(tmp_path / "unmapped.csv")
    assert len(facts) == 51
    assert len(unmapped) == 10
    assert facts["concept_cd"].notna().all()


def test_run_aborts_when_validator_rejects_bundle():
    importer = RecordingImporter()

    with pytest.raises(InvalidBundleError, match="validation"):
        run(FIXTURES / "bundle_min.json", importer, validator=RejectAll())

    assert importer.calls == []