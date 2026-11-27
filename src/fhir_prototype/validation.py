import json
import logging
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
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


class HapiValidator(BundleValidator):
    """Validates bundles locally with the HL7 FHIR validator, without a terminology server."""

    def __init__(self, profiles: set[str], java: str, jar: Path, ig: Path, fhir_home: Path) -> None:
        if shutil.which(java) is None:
            raise FileNotFoundError(f"Java not found: {java}")
        if not jar.is_file():
            raise FileNotFoundError(f"FHIR validator not found: {jar}")
        self.profiles = profiles
        self.java = java
        self.jar = jar
        self.ig = ig
        self.fhir_home = fhir_home

    def is_valid(self, bundle: dict[str, Any]) -> bool:
        selected, ignored = select_resources(bundle, self.profiles)
        if ignored:
            logger.info("Ignored %d resources with a profile outside the mapping", ignored)
        with tempfile.TemporaryDirectory() as tmp:
            bundle_file = Path(tmp) / "bundle.json"
            outcome_file = Path(tmp) / "outcome.json"
            bundle_file.write_text(json.dumps(selected), encoding="utf-8")
            command = [
                self.java,
                f"-Duser.home={self.fhir_home}",
                "-jar",
                str(self.jar),
                str(bundle_file),
                "-version",
                "4.0.1",
                "-ig",
                str(self.ig),
                "-tx",
                "n/a",
                "-output",
                str(outcome_file),
            ]
            # Exit code 1 only means that the bundle has errors, the outcome file tells the rest.
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            if not outcome_file.is_file():
                raise RuntimeError(
                    f"FHIR validator wrote no result (exit code {completed.returncode}): {completed.stderr}"
                )
            return outcome_is_valid(json.loads(outcome_file.read_text(encoding="utf-8")))
