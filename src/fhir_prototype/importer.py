from abc import ABC, abstractmethod
from pathlib import Path

from fhir_prototype.facts import MappingResult
from fhir_prototype.frames import BundleFrames


class Importer(ABC):
    """Writes the patients, encounters and facts of one bundle to a target."""

    @abstractmethod
    def write(self, frames: BundleFrames, result: MappingResult) -> None: ...


class CsvImporter(Importer):
    """Writes the result of one bundle as CSV files into one directory."""

    def __init__(self, output_dir: str | Path) -> None:
        self._output_dir = Path(output_dir)

    def write(self, frames: BundleFrames, result: MappingResult) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        frames.patients.to_csv(self._output_dir / "patients.csv", index=False)
        frames.encounters.to_csv(self._output_dir / "encounters.csv", index=False)
        result.facts.to_csv(self._output_dir / "facts.csv", index=False)
        result.unmapped.to_csv(self._output_dir / "unmapped.csv", index=False)