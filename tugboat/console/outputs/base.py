from __future__ import annotations

import typing
from abc import ABC, abstractmethod

if typing.TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path
    from typing import TextIO

    from tugboat.analyze import AugmentedDiagnosis


class OutputBuilder(ABC):
    """
    Abstract base class for building diagnostic output.
    """

    @abstractmethod
    def update(
        self, *, path: Path, content: str, diagnoses: Sequence[AugmentedDiagnosis]
    ) -> None:
        """Write a diagnostic message for a given path."""

    @abstractmethod
    def dump(self, stream: TextIO) -> None:
        """Serialize the data to a stream."""
