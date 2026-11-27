import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)

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


def _message(issue: dict[str, Any]) -> str:
    text = issue.get("details", {}).get("text", "")
    expression = issue.get("expression", [])
    return f"{expression[0]}: {text}" if expression else text


def outcome_is_valid(outcome: dict[str, Any]) -> bool:
    """Log the errors and warnings of a validator OperationOutcome, return False if there is a fatal or error issue."""
    valid = True
    for issue in outcome.get("issue", []):
        severity = issue.get("severity")
        if severity in ("fatal", "error"):
            logger.error(_message(issue))
            valid = False
        elif severity == "warning":
            logger.warning(_message(issue))
    return valid


class BundleValidator(ABC):
    """Decides whether a FHIR bundle may be processed."""

    @abstractmethod
    def is_valid(self, bundle: dict[str, Any]) -> bool: ...


class NoValidation(BundleValidator):
    """Placeholder that accepts every bundle until the external validation is available."""

    def is_valid(self, bundle: dict[str, Any]) -> bool:
        return True
