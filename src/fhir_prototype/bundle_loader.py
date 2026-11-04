import json
from pathlib import Path
from typing import Any


class InvalidBundleError(ValueError):
    """Raised when the input is not a usable FHIR bundle."""


def load_bundle(path: str | Path) -> dict[str, Any]:
    """Read a JSON file and return it as a FHIR bundle dict."""
    text = Path(path).read_text(encoding="utf-8")
    return parse_bundle(text)


def parse_bundle(text: str) -> dict[str, Any]:
    """Parse a JSON string and check that it is a FHIR bundle."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise InvalidBundleError(f"Input is not valid JSON: {e}") from e

    if not isinstance(data, dict) or data.get("resourceType") != "Bundle":
        found = data.get("resourceType") if isinstance(data, dict) else type(data).__name__
        raise InvalidBundleError(f"Expected resourceType 'Bundle', got {found!r}")

    return data