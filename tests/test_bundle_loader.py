import json
from pathlib import Path

import pytest

from fhir_prototype.bundle_loader import InvalidBundleError, load_bundle

FIXTURES = Path(__file__).parent / "fixtures"


def test_loads_bundle_from_file():
    bundle = load_bundle(FIXTURES / "bundle_min.json")

    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert len(bundle["entry"]) == 68


def test_rejects_json_that_is_not_a_bundle(tmp_path):
    path = tmp_path / "patient.json"
    path.write_text(json.dumps({"resourceType": "Patient", "id": "p1"}))

    with pytest.raises(InvalidBundleError, match="Bundle"):
        load_bundle(path)


def test_rejects_malformed_json(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text('{"resourceType": "Bundle", ')

    with pytest.raises(InvalidBundleError, match="JSON"):
        load_bundle(path)