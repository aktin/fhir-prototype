from abc import ABC, abstractmethod
from typing import Any

# No profile in the mapping, validated against FHIR R4 core.
CORE_TYPES = {"Patient", "Encounter"}


def select_resources(bundle: dict[str, Any], profiles: set[str]) -> tuple[dict[str, Any], int]:
    """Return a copy of the bundle with only the resources to validate, and the number of ignored resources."""
    kept = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") in CORE_TYPES or profiles & set(resource.get("meta", {}).get("profile", [])):
            kept.append(entry)
    return {**bundle, "entry": kept}, len(bundle.get("entry", [])) - len(kept)


class BundleValidator(ABC):
    """Decides whether a FHIR bundle may be processed."""

    @abstractmethod
    def is_valid(self, bundle: dict[str, Any]) -> bool: ...


class NoValidation(BundleValidator):
    """Placeholder that accepts every bundle until the external validation is available."""

    def is_valid(self, bundle: dict[str, Any]) -> bool:
        return True
