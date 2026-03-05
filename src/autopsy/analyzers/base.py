from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from autopsy.models import FileResult

if TYPE_CHECKING:
    from autopsy.config import Config


class BaseAnalyzer(ABC):
    """Contract for all language-specific analyzers."""

    @abstractmethod
    def analyze(self, path: Path, source: str, config: Config | None = None) -> FileResult:
        """Analyze source code at path and return a FileResult."""
        ...
