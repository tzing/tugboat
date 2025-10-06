from __future__ import annotations

import typing
from abc import ABC, abstractmethod

if typing.TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import TextIO

    from tugboat.engine import DiagnosisModel


class OutputFormatter(ABC):
    """Abstract base class for building output."""

    @abstractmethod
    def update(self, *, content: str, diagnoses: Sequence[DiagnosisModel]) -> None:
        """Update the data to be serialized."""

    @abstractmethod
    def dump(self, stream: TextIO) -> None:
        """Serialize the data to a stream."""
