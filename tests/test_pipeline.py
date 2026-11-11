import pandas as pd
import pytest

from fhir_prototype.bundle_loader import InvalidBundleError
from fhir_prototype.pipeline import run
from fhir_prototype.validation import BundleValidator
from helpers import FIXTURES


def test_run_writes_facts_and_unmapped_csv(tmp_path):
    run(FIXTURES / "bundle_min.json", tmp_path)

    facts = pd.read_csv(tmp_path / "facts.csv")
    unmapped = pd.read_csv(tmp_path / "unmapped.csv")
    assert len(facts) == 51
    assert len(unmapped) == 10
    assert facts["concept_cd"].notna().all()


class RejectAll(BundleValidator):
    def is_valid(self, bundle):
        return False


def test_run_aborts_when_validator_rejects_bundle(tmp_path):
    with pytest.raises(InvalidBundleError, match="validation"):
        run(FIXTURES / "bundle_min.json", tmp_path, validator=RejectAll())

    assert not (tmp_path / "facts.csv").exists()
