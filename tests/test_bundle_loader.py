import json
import re
import zipfile

import pytest

from fhir_prototype.bundle_loader import InvalidBundleError, load_bundle, load_zip, parse_bundle
from helpers import FIXTURES, PATIENT, make_bundle


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


def test_parse_bundle_returns_bundle_dict():
    bundle = parse_bundle(json.dumps(make_bundle(PATIENT)), "inline")

    assert bundle["resourceType"] == "Bundle"
    assert bundle["entry"][0]["resource"] == PATIENT


def test_parse_bundle_names_source_when_json_is_malformed():
    with pytest.raises(InvalidBundleError, match="broken.json.*JSON"):
        parse_bundle('{"resourceType": "Bundle", ', "broken.json")


def test_parse_bundle_names_source_when_not_a_bundle():
    with pytest.raises(InvalidBundleError, match="patient.json.*Bundle"):
        parse_bundle(json.dumps(PATIENT), "patient.json")


def test_load_bundle_names_file_in_error(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text('{"resourceType": "Bundle", ')

    with pytest.raises(InvalidBundleError, match=re.escape(str(path))):
        load_bundle(path)


def _write_zip(path, entries):
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return path


def test_load_zip_returns_bundle_of_single_json(tmp_path):
    text = (FIXTURES / "bundle_min.json").read_text(encoding="utf-8")
    path = _write_zip(tmp_path / "delivery.zip", {"bundle_min.json": text})

    bundles = load_zip(path)

    assert len(bundles) == 1
    assert bundles[0] == load_bundle(FIXTURES / "bundle_min.json")
