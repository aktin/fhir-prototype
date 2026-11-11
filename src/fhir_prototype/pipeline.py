from pathlib import Path

from fhir_prototype.bundle_loader import load_bundle
from fhir_prototype.facts import MappingResult, build_facts
from fhir_prototype.frames import bundle_to_frames
from fhir_prototype.mapping import load_mapping
from fhir_prototype.processing import process


def run(bundle_path: str | Path, output_dir: str | Path) -> MappingResult:
    """Run the whole pipeline for one bundle file and write the results as CSV."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    bundle = load_bundle(bundle_path)
    frames = process(bundle_to_frames(bundle))
    result = build_facts(frames, load_mapping())

    result.facts.to_csv(output_dir / "facts.csv", index=False)
    result.unmapped.to_csv(output_dir / "unmapped.csv", index=False)
    return result