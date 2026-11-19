import json
import zipfile
from pathlib import Path
from typing import Any


class InvalidBundleError(ValueError):
    """Raised when the input is not a usable FHIR bundle."""


def load_bundle(path: str | Path) -> dict[str, Any]:
    """Read a JSON file and return it as a FHIR bundle dict."""
    text = Path(path).read_text(encoding="utf-8")
    return parse_bundle(text, str(path))


def parse_bundle(text: str, source: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise InvalidBundleError(f"{source} is not valid JSON: {e}") from e

    if not isinstance(data, dict) or data.get("resourceType") != "Bundle":
        found = data.get("resourceType") if isinstance(data, dict) else type(data).__name__
        raise InvalidBundleError(f"{source}: expected resourceType 'Bundle', got {found!r}")

    return data


def load_zip(path: str | Path) -> list[dict[str, Any]]:
    with zipfile.ZipFile(path) as archive:
        return [parse_bundle(archive.read(name).decode("utf-8"), f"{path}:{name}") for name in archive.namelist()]
