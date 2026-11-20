import logging
from pathlib import Path
from typing import Any

from fhir_prototype.bundle_index import BundleIndex, UnresolvedReferenceError
from fhir_prototype.bundle_loader import InvalidBundleError, load_zip
from fhir_prototype.dates import parse_dates
from fhir_prototype.facts import build_facts
from fhir_prototype.frames import bundle_to_frames
from fhir_prototype.importer import Importer
from fhir_prototype.mapping import load_mapping
from fhir_prototype.validation import BundleValidator, NoValidation

logger = logging.getLogger(__name__)


def _run_bundle(
    name: str,
    bundle: dict[str, Any],
    importer: Importer,
    validator: BundleValidator,
    mapping: list[dict[Any, Any]],
) -> None:
    """Run all steps for one bundle and hand the result to the importer."""
    if not validator.is_valid(bundle):
        raise InvalidBundleError(f"{name} failed validation")
    index = BundleIndex(bundle)
    frames = parse_dates(bundle_to_frames(index))
    result = build_facts(index, mapping)
    importer.write(name, frames, result)


def run(
    zip_path: str | Path,
    importer: Importer,
    validator: BundleValidator = NoValidation(),
) -> None:
    """Run the pipeline for every bundle in a ZIP file.

    Bundles that fail are skipped with a warning. Raises InvalidBundleError if
    no bundle could be processed.
    """
    mapping = load_mapping()
    processed = 0
    for name, bundle in load_zip(zip_path).items():
        try:
            _run_bundle(name, bundle, importer, validator, mapping)
        except (InvalidBundleError, UnresolvedReferenceError) as e:
            logger.warning("Skipping bundle %s: %s", name, e)
        else:
            processed += 1

    if processed == 0:
        raise InvalidBundleError(f"{zip_path}: no bundle could be processed")
