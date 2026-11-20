import json
import re
import zipfile

import pytest

from fhir_prototype.bundle_loader import InvalidBundleError, load_bundle, load_zip
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

    with pytest.raises(InvalidBundleError, match=f"{re.escape(str(path))}.*JSON"):
        load_bundle(path)


def _write_zip(path, entries):
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return path


def test_load_zip_returns_bundles_sorted_by_file_name(tmp_path):
    names = ["bundle_max_2.json", "bundle_min.json", "bundle_max_1.json"]
    entries = {name: (FIXTURES / name).read_text(encoding="utf-8") for name in names}
    path = _write_zip(tmp_path / "delivery.zip", entries)

    bundles = load_zip(path)

    assert bundles == [load_bundle(FIXTURES / name) for name in sorted(names)]


def test_load_zip_ignores_entries_in_subfolders(tmp_path):
    text = (FIXTURES / "bundle_min.json").read_text(encoding="utf-8")
    path = _write_zip(
        tmp_path / "delivery.zip",
        {
            "bundle_min.json": text,
            "__MACOSX/._bundle_min.json": "not json at all",
            "nested/other.json": json.dumps(make_bundle(PATIENT)),
        },
    )

    bundles = load_zip(path)

    assert bundles == [load_bundle(FIXTURES / "bundle_min.json")]


def test_load_zip_ignores_entries_that_are_not_json(tmp_path):
    text = (FIXTURES / "bundle_min.json").read_text(encoding="utf-8")
    path = _write_zip(
        tmp_path / "delivery.zip",
        {
            "README.txt": "Delivery from CSV2FHIR",
            "bundle_min.json": text,
            "notes.md": "# Notes",
            "upper.JSON": json.dumps(make_bundle(PATIENT)),
        },
    )

    bundles = load_zip(path)

    assert len(bundles) == 2
    assert bundles[0] == load_bundle(FIXTURES / "bundle_min.json")


def test_load_zip_rejects_file_that_is_not_a_zip(tmp_path):
    path = tmp_path / "delivery.zip"
    path.write_text("not a zip")

    with pytest.raises(InvalidBundleError, match=f"{re.escape(str(path))}.*not a ZIP"):
        load_zip(path)


def test_load_zip_rejects_zip_without_json(tmp_path):
    path = _write_zip(tmp_path / "delivery.zip", {"README.txt": "Delivery from CSV2FHIR"})

    with pytest.raises(InvalidBundleError, match="no JSON"):
        load_zip(path)


def test_load_zip_skips_malformed_json_with_warning(tmp_path, caplog):
    entries = {name: (FIXTURES / name).read_text(encoding="utf-8") for name in ["bundle_min.json", "bundle_max_1.json"]}
    entries["broken.json"] = '{"resourceType": "Bundle", '
    path = _write_zip(tmp_path / "delivery.zip", entries)

    bundles = load_zip(path)

    assert bundles == [load_bundle(FIXTURES / "bundle_max_1.json"), load_bundle(FIXTURES / "bundle_min.json")]
    assert len(caplog.records) == 1
    assert re.search(r"delivery\.zip:broken\.json.*JSON", caplog.records[0].getMessage())


def test_load_zip_skips_json_that_is_not_a_bundle(tmp_path, caplog):
    text = (FIXTURES / "bundle_min.json").read_text(encoding="utf-8")
    path = _write_zip(tmp_path / "delivery.zip", {"bundle_min.json": text, "patient.json": json.dumps(PATIENT)})

    bundles = load_zip(path)

    assert bundles == [load_bundle(FIXTURES / "bundle_min.json")]
    assert len(caplog.records) == 1
    assert re.search(r"delivery\.zip:patient\.json.*Bundle", caplog.records[0].getMessage())


def test_load_zip_rejects_zip_without_valid_bundle(tmp_path, caplog):
    path = _write_zip(
        tmp_path / "delivery.zip",
        {"broken.json": '{"resourceType": "Bundle", ', "patient.json": json.dumps(PATIENT)},
    )

    with (
        pytest.raises(InvalidBundleError, match=r"delivery\.zip contains no valid bundles"),
    ):
        load_zip(path)

    assert len(caplog.records) == 2


def test_load_zip_names_entry_that_is_not_utf8(tmp_path):
    path = _write_zip(tmp_path / "delivery.zip", {"bad.json": b"\xff"})

    with pytest.raises(InvalidBundleError, match=r"delivery\.zip:bad\.json could not be read"):
        load_zip(path)


def test_load_zip_names_entry_with_crc_mismatch(tmp_path):
    content = json.dumps(make_bundle(PATIENT)).encode("utf-8")
    path = tmp_path / "delivery.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("bundle.json", content)

    data = bytearray(path.read_bytes())
    data[data.index(content)] ^= 0x01
    path.write_bytes(bytes(data))

    with pytest.raises(InvalidBundleError, match=r"delivery\.zip:bundle\.json could not be read"):
        load_zip(path)


def test_load_bundle_names_file_that_is_not_utf8(tmp_path):
    path = tmp_path / "bad.json"
    path.write_bytes(b"\xff")

    with pytest.raises(InvalidBundleError, match=re.escape(str(path))):
        load_bundle(path)


def test_load_bundle_accepts_utf8_bom(tmp_path):
    path = tmp_path / "bom.json"
    path.write_text("\ufeff" + json.dumps(make_bundle(PATIENT)), encoding="utf-8")

    assert load_bundle(path) == make_bundle(PATIENT)


def test_load_zip_accepts_utf8_bom(tmp_path):
    path = _write_zip(tmp_path / "delivery.zip", {"bom.json": "\ufeff" + json.dumps(make_bundle(PATIENT))})

    assert load_zip(path) == [make_bundle(PATIENT)]


def test_load_zip_rejects_duplicate_entry_names(tmp_path):
    path = tmp_path / "delivery.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("bundle.json", json.dumps(make_bundle(PATIENT)))
        with pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr("bundle.json", json.dumps(make_bundle(PATIENT)))

    with pytest.raises(InvalidBundleError, match=r"delivery\.zip.*duplicate.*bundle\.json"):
        load_zip(path)


def test_load_zip_raises_file_not_found_for_missing_archive(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_zip(tmp_path / "missing.zip")
