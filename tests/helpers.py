from pathlib import Path

BASE = "https://fhir.example.org"
PATIENT = {"resourceType": "Patient", "id": "p1"}
FIXTURES = Path(__file__).parent / "fixtures"


def make_encounter(**overrides):
    encounter = {
        "resourceType": "Encounter",
        "id": "e1",
        "identifier": [{"system": "urn:eid", "value": "E-1"}],
        "status": "finished",
        "class": {"code": "IMP"},
        "subject": {"reference": f"{BASE}/Patient/p1"},
        "period": {
            "start": "2024-01-15T09:00:00+01:00",
            "end": "2024-01-19T12:00:00+01:00",
        },
    }
    encounter.update(overrides)
    return encounter


ENCOUNTER = make_encounter()


def make_observation(**overrides):
    observation = {
        "resourceType": "Observation",
        "id": "o1",
        "meta": {"profile": ["https://example.org/StructureDefinition/heartrate"]},
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]},
        "subject": {"reference": f"{BASE}/Patient/p1"},
        "encounter": {"reference": f"{BASE}/Encounter/e1"},
        "effectiveDateTime": "2024-01-15T09:00:00+01:00",
        "valueQuantity": {"value": 80, "unit": "/min", "code": "/min"},
    }
    observation.update(overrides)
    return observation


def make_bundle(*resources):
    """Wrap resources into a collection bundle, fullUrl = BASE/Type/id."""
    bundle = {"resourceType": "Bundle", "type": "collection", "entry": []}
    for resource in resources:
        bundle["entry"].append({
            "fullUrl": f"{BASE}/{resource['resourceType']}/{resource['id']}",
            "resource": resource,
        })
    return bundle
