from abc import ABC, abstractmethod
from typing import Any


class BundleValidator(ABC):
    """Decides whether a FHIR bundle may be processed."""

    @abstractmethod
    def is_valid(self, bundle: dict[str, Any]) -> bool: ...


class NoValidation(BundleValidator):
    """Placeholder that accepts every bundle until the external validation is available."""

    def is_valid(self, bundle: dict[str, Any]) -> bool:
        return True
