from pathlib import Path

import pytest
from helpers import make_bundle

from fhir_prototype.bundle_index import BundleIndex, UnresolvedReferenceError
from fhir_prototype.bundle_loader import InvalidBundleError, load_bundle

FIXTURES = Path(__file__).parent / "fixtures"
BASE = "https://fhir.example.org"


def test_of_type_returns_only_resources_of_that_type():
    patient = {"resourceType": "Patient", "id": "p1"}
    obs1 = {"resourceType": "Observation", "id": "o1"}
    obs2 = {"resourceType": "Observation", "id": "o2"}
    index = BundleIndex(make_bundle(patient, obs1, obs2))

    result = index.of_type("Observation")

    assert result == [obs1, obs2]


def test_of_type_returns_empty_list_for_missing_type():
    patient = {"resourceType": "Patient", "id": "p1"}
    index = BundleIndex(make_bundle(patient))

    result = index.of_type("Encounter")

    assert result == []


def test_resolve_returns_referenced_resource():
    patient = {"resourceType": "Patient", "id": "p1"}
    obs = {
        "resourceType": "Observation",
        "id": "o1",
        "subject": {"reference": f"{BASE}/Patient/p1"},
    }
    index = BundleIndex(make_bundle(patient, obs))

    result = index.resolve(obs["subject"]["reference"])

    assert result is patient


def test_resolve_raises_for_unknown_reference():
    index = BundleIndex(make_bundle({"resourceType": "Patient", "id": "p1"}))
    missing = f"{BASE}/Patient/does-not-exist"

    with pytest.raises(UnresolvedReferenceError, match=missing):
        index.resolve(missing)


def test_all_observation_references_resolve_in_max_bundle():
    index = BundleIndex(load_bundle(FIXTURES / "bundle_max_1.json"))

    for obs in index.of_type("Observation"):
        assert index.resolve(obs["subject"]["reference"])["resourceType"] == "Patient"
        assert index.resolve(obs["encounter"]["reference"])["resourceType"] == "Encounter"
        if "device" in obs:
            assert index.resolve(obs["device"]["reference"])["resourceType"] == "DeviceMetric"


def test_rejects_entry_without_full_url():
    bundle = make_bundle({"resourceType": "Patient", "id": "p1"},
                         {"resourceType": "Observation", "id": "o1"})
    del bundle["entry"][1]["fullUrl"]

    with pytest.raises(InvalidBundleError, match="Entry 1"):
        BundleIndex(bundle)


def test_rejects_entry_without_resource():
    bundle = make_bundle({"resourceType": "Patient", "id": "p1"},
                         {"resourceType": "Observation", "id": "o1"})
    del bundle["entry"][1]["resource"]

    with pytest.raises(InvalidBundleError, match="Entry 1"):
        BundleIndex(bundle)


def test_rejects_repeated_full_url():
    first = {"resourceType": "Patient", "id": "p1", "gender": "female"}
    second = {"resourceType": "Patient", "id": "p1", "gender": "male"}
    bundle = make_bundle(first, second)

    with pytest.raises(InvalidBundleError, match=f"Entry 1 repeats.*{BASE}/Patient/p1"):
        BundleIndex(bundle)
