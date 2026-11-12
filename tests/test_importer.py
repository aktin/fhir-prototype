import pandas as pd
from helpers import ENCOUNTER, PATIENT, make_bundle

from fhir_prototype.bundle_index import BundleIndex
from fhir_prototype.facts import MappingResult
from fhir_prototype.frames import bundle_to_frames
from fhir_prototype.importer import CsvImporter


def make_result():
    return MappingResult(
        facts=pd.DataFrame({"resource_id": ["o1", "o2"], "concept_cd": ["LOINC:8867-4", "LOINC:9279-1"]}),
        unmapped=pd.DataFrame({"resource_id": ["o3"], "concept_cd": [None]}),
    )


def test_csv_importer_writes_four_files(tmp_path):
    frames = bundle_to_frames(BundleIndex(make_bundle(PATIENT, ENCOUNTER)))

    CsvImporter(tmp_path).write(frames, make_result())

    assert len(pd.read_csv(tmp_path / "patients.csv")) == 1
    assert len(pd.read_csv(tmp_path / "encounters.csv")) == 1
    assert len(pd.read_csv(tmp_path / "facts.csv")) == 2
    assert len(pd.read_csv(tmp_path / "unmapped.csv")) == 1


def test_csv_importer_creates_missing_directory(tmp_path):
    target = tmp_path / "out" / "run1"
    frames = bundle_to_frames(BundleIndex(make_bundle(PATIENT, ENCOUNTER)))

    CsvImporter(target).write(frames, make_result())

    assert (target / "facts.csv").exists()


def test_csv_importer_does_not_write_index_column(tmp_path):
    frames = bundle_to_frames(BundleIndex(make_bundle(PATIENT, ENCOUNTER)))

    CsvImporter(tmp_path).write(frames, make_result())

    assert list(pd.read_csv(tmp_path / "facts.csv").columns) == ["resource_id", "concept_cd"]
