from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from typing import Any, Literal


class AugmentedDiagnosis(typing.TypedDict):
    """
    The augmented diagnosis reported by the analyzer.

    This type extends the :py:class:`tugboat.types.Diagnosis` and adds additional
    fields to provide more context about the diagnosis.
    """

    line: int
    """
    Line number of the issue occurrence in the source file.
    Note that the line number is cumulative across all documents in the YAML file.
    """

    column: int
    """
    Column number of the issue occurrence in the source file.
    """

    type: Literal["error", "failure", "warning"]
    """The type that describes the severity."""

    code: str
    """Diagnosis code."""

    manifest: str | None
    """The manifest name where the issue occurred."""

    loc: tuple[str | int, ...]
    """
    The location of the issue occurrence within the manifest, specified in a
    path-like format.
    """

    summary: str
    """The summary."""

    msg: str
    """The detailed message."""

    input: Any | None
    """The input that caused the issue."""

    fix: str | None
    """The possible fix for the issue."""
