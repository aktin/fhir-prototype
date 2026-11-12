from pathlib import Path

from fhir_prototype.bundle_loader import InvalidBundleError, load_bundle
from fhir_prototype.facts import MappingResult, build_facts
from fhir_prototype.frames import bundle_to_frames
from fhir_prototype.importer import Importer
from fhir_prototype.mapping import load_csv_mapping
from fhir_prototype.processing import process
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
    frames = process(bundle_to_frames(bundle))
    result = build_facts(frames, load_csv_mapping())
    importer.write(frames, result)
    return result
