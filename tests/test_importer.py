import pandas as pd

from fhir_prototype.bundle_index import BundleIndex
from fhir_prototype.facts import MappingResult
from fhir_prototype.frames import bundle_to_frames
from fhir_prototype.importer import CsvImporter
from helpers import ENCOUNTER, PATIENT, make_bundle


def make_result():
    return MappingResult(
        facts=pd.DataFrame({"resource_id": ["o1", "o2"], "concept_cd": ["LOINC:8867-4", "LOINC:9279-1"]}),
        unmapped=pd.DataFrame({"resource_id": ["o3"], "concept_cd": [None]}),
    )


def test_csv_importer_writes_four_files_into_bundle_folder(tmp_path):
    frames = bundle_to_frames(BundleIndex(make_bundle(PATIENT, ENCOUNTER)))

    CsvImporter(tmp_path).write("bundle_1.json", frames, make_result())

    folder = tmp_path / "bundle_1"
    assert len(pd.read_csv(folder / "patients.csv")) == 1
    assert len(pd.read_csv(folder / "encounters.csv")) == 1
    assert len(pd.read_csv(folder / "facts.csv")) == 2
    assert len(pd.read_csv(folder / "unmapped.csv")) == 1


def test_csv_importer_creates_missing_directory(tmp_path):
    target = tmp_path / "out" / "run1"
    frames = bundle_to_frames(BundleIndex(make_bundle(PATIENT, ENCOUNTER)))

    CsvImporter(target).write("bundle_1.json", frames, make_result())

    assert (target / "bundle_1" / "facts.csv").exists()


def test_csv_importer_does_not_write_index_column(tmp_path):
    frames = bundle_to_frames(BundleIndex(make_bundle(PATIENT, ENCOUNTER)))

    CsvImporter(tmp_path).write("bundle_1.json", frames, make_result())

    assert list(pd.read_csv(tmp_path / "bundle_1" / "facts.csv").columns) == ["resource_id", "concept_cd"]


def test_csv_importer_keeps_bundles_apart(tmp_path):
    frames = bundle_to_frames(BundleIndex(make_bundle(PATIENT, ENCOUNTER)))
    one_fact = MappingResult(
        facts=pd.DataFrame({"resource_id": ["o9"], "concept_cd": ["LOINC:8867-4"]}),
        unmapped=pd.DataFrame({"resource_id": [], "concept_cd": []}),
    )
    importer = CsvImporter(tmp_path)

    importer.write("bundle_1.json", frames, make_result())
    importer.write("bundle_2.json", frames, one_fact)

    assert len(pd.read_csv(tmp_path / "bundle_1" / "facts.csv")) == 2
    assert len(pd.read_csv(tmp_path / "bundle_2" / "facts.csv")) == 1
