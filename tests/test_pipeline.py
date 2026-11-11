import pandas as pd

from fhir_prototype.pipeline import run
from helpers import FIXTURES


def test_run_writes_facts_and_unmapped_csv(tmp_path):
    run(FIXTURES / "bundle_min.json", tmp_path)

    facts = pd.read_csv(tmp_path / "facts.csv")
    unmapped = pd.read_csv(tmp_path / "unmapped.csv")
    assert len(facts) == 43
    assert len(unmapped) == 18
    assert facts["concept_cd"].notna().all()