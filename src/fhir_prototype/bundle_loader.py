import json
import logging
import lzma
import zipfile
import zlib
from collections import Counter
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class InvalidBundleError(ValueError):
    """Raised when the input is not a usable FHIR bundle."""


def _read_entry(archive: zipfile.ZipFile, name: str, source: str) -> str:
    try:
        return archive.read(name).decode("utf_8_sig")
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


def load_zip(path: str | Path) -> dict[str, dict[str, Any]]:
    """Read all bundles from the JSON files in the root of a ZIP archive.

    Returns a dict from file name to bundle, sorted by file name. Entries that
    are not valid JSON or not a Bundle are skipped with a warning. Entries that
    cannot be read raise InvalidBundleError, because they point to a damaged
    archive.
    """
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

        bundles: dict[str, dict[str, Any]] = {}
        for name in names:
            source = f"{path}:{name}"
            text = _read_entry(archive, name, source)
            try:
                bundles[name] = _parse_bundle(text, source)
            except InvalidBundleError as e:
                logger.warning("Skipping ZIP entry: %s", e)

    if not bundles:
        raise InvalidBundleError(f"{path} contains no valid bundles")
    return bundles
