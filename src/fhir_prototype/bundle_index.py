from typing import Any

Resource = dict[str, Any]


class UnresolvedReferenceError(KeyError):
    """Raised when a reference points to no resource in the bundle."""


class BundleIndex:
    """Lookup structure over the entries of one FHIR bundle."""

    def __init__(self, bundle: dict[str, Any]) -> None:
        self._by_full_url: dict[str, Resource] = {}
        for entry in bundle.get("entry", []):
            self._by_full_url[entry["fullUrl"]] = entry["resource"]

    def of_type(self, resource_type: str) -> list[Resource]:
        return [
            resource
            for resource in self._by_full_url.values()
            if resource["resourceType"] == resource_type
        ]

    def resolve(self, reference: str) -> Resource:
        try:
            return self._by_full_url[reference]
        except KeyError:
            raise UnresolvedReferenceError(reference) from None