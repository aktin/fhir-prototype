import pytest

from fhir_prototype.bundle_loader import load_bundle
from fhir_prototype.frames import bundle_to_frames
from fhir_prototype.mapping import load_mapping
from helpers import FIXTURES


def test_load_mapping_has_expected_columns():
    mapping = load_mapping()

    assert list(mapping.columns) == [
        "resource_type",
        "profile",
        "device_category",
        "concept_cd",
        "valtype_cd",
        "value_column",
        "expected_unit",
        "status",
        "open_question",
        "note",
    ]


def test_mapping_has_unique_profile_and_device_category():
    mapping = load_mapping()

    assert not mapping.duplicated(subset=["profile", "device_category"]).any()


@pytest.mark.parametrize("fixture", [
    "bundle_min.json",
    "bundle_max_1.json",
    "bundle_max_2.json",
])
def test_mapping_covers_all_observations_in_fixtures(fixture):
    observations = bundle_to_frames(load_bundle(FIXTURES / fixture)).observations
    mapping = load_mapping()

    observation_keys = set(zip(observations["profile"], observations["device_category"]))
    mapping_keys = set(zip(mapping["profile"], mapping["device_category"]))

    assert observation_keys - mapping_keys == set()
