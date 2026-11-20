from abc import ABC, abstractmethod
from pathlib import Path

from fhir_prototype.facts import MappingResult
from fhir_prototype.frames import BundleFrames


class Importer(ABC):
    """Writes the patients, encounters and facts of one bundle to a target."""

    @abstractmethod
    def write(self, name: str, frames: BundleFrames, result: MappingResult) -> None: ...


class CsvImporter(Importer):
    """Writes the result of each bundle as CSV files into its own subfolder."""

    def __init__(self, output_dir: str | Path) -> None:
        self._output_dir = Path(output_dir)

    def write(self, name: str, frames: BundleFrames, result: MappingResult) -> None:
        folder = self._output_dir / Path(name).stem
        folder.mkdir(parents=True, exist_ok=True)
        frames.patients.to_csv(folder / "patients.csv", index=False)
        frames.encounters.to_csv(folder / "encounters.csv", index=False)
        result.facts.to_csv(folder / "facts.csv", index=False)
        result.unmapped.to_csv(folder / "unmapped.csv", index=False)
