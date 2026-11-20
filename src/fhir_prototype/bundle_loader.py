import json
import lzma
import zipfile
import zlib
from collections import Counter
from pathlib import Path
from typing import Any


class InvalidBundleError(ValueError):
    """Raised when the input is not a usable FHIR bundle."""


def _load_entry(archive: zipfile.ZipFile, path: str | Path, name: str) -> dict[str, Any]:
    source = f"{path}:{name}"
    try:
        text = archive.read(name).decode("utf_8_sig")
    except (
        UnicodeDecodeError,
        zipfile.BadZipFile,
        zlib.error,
        lzma.LZMAError,
        EOFError,
        OSError,
        RuntimeError,
    ) as e:
        raise InvalidBundleError(f"{source} could not be read: {e}") from e
    return _parse_bundle(text, source)


def load_bundle(path: str | Path) -> dict[str, Any]:
    """Read a JSON file and return it as a FHIR bundle dict."""
    try:
        text = Path(path).read_text(encoding="utf_8_sig")
    except UnicodeDecodeError as e:
        raise InvalidBundleError(f"{path} could not be read: {e}") from e
    return _parse_bundle(text, str(path))


def _parse_bundle(text: str, source: str) -> dict[str, Any]:
    """Parse JSON text into a FHIR bundle dict, naming source in errors."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise InvalidBundleError(f"{source} is not valid JSON: {e}") from e

    if not isinstance(data, dict) or data.get("resourceType") != "Bundle":
        found = data.get("resourceType") if isinstance(data, dict) else type(data).__name__
        raise InvalidBundleError(f"{source}: expected resourceType 'Bundle', got {found!r}")

    return data


def load_zip(path: str | Path) -> list[dict[str, Any]]:
    """Read all bundles from the JSON files in the root of a ZIP archive."""
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as e:
        raise InvalidBundleError(f"{path} is not a ZIP file") from e

    with archive:
        names = sorted(name for name in archive.namelist() if "/" not in name and name.lower().endswith(".json"))
        if not names:
            raise InvalidBundleError(f"{path} contains no JSON files")
        duplicates = [name for name, count in Counter(names).items() if count > 1]
        if duplicates:
            raise InvalidBundleError(f"{path} contains duplicate entries: {', '.join(duplicates)}")
        return [_load_entry(archive, path, name) for name in names]
