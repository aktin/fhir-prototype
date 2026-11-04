BASE = "https://fhir.example.org"

def make_bundle(*resources):
    """Wrap resources into a collection bundle, fullUrl = BASE/Type/id."""
    bundle = {"resourceType": "Bundle", "type": "collection", "entry": []}
    for resource in resources:
        bundle["entry"].append({
            "fullUrl": f"{BASE}/{resource['resourceType']}/{resource['id']}",
            "resource": resource,
        })
    return bundle