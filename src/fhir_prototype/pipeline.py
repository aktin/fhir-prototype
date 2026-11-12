from pathlib import Path

from fhir_prototype.bundle_index import BundleIndex
from fhir_prototype.bundle_loader import InvalidBundleError, load_bundle
from fhir_prototype.facts import MappingResult, build_facts
from fhir_prototype.frames import bundle_to_frames
from fhir_prototype.importer import Importer
from fhir_prototype.mapping import load_mapping
from fhir_prototype.dates import parse_dates
from fhir_prototype.validation import BundleValidator, NoValidation


def run(
        bundle_path: str | Path,
        importer: Importer,
        validator: BundleValidator = NoValidation(),
) -> MappingResult:
    """Run the whole pipeline for one bundle file and hand the result to the importer."""
    bundle = load_bundle(bundle_path)
    if not validator.is_valid(bundle):
        raise InvalidBundleError(f"Bundle {bundle_path} failed validation")
    index = BundleIndex(bundle)
    frames = parse_dates(bundle_to_frames(index))
    result = build_facts(index, load_mapping())
    importer.write(frames, result)
    return result
