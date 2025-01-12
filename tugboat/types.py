from __future__ import annotations

import typing


if typing.TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any, Literal, NotRequired


class Diagnosis(typing.TypedDict):
    """
    A diagnosis reported by the analyzer.

    This class serves as the fundamental structure for a diagnosis. It is used
    to report issues identified by the analyzer. All analyzers must return a
    diagnosis or a list of diagnoses when they are registered with the framework.
    """

    type: NotRequired[Literal["error", "failure", "skipped"]]
    """
    The diagnosis type.
    When not provided, it defaults to "failure".
    """

    code: str
    """Diagnosis code."""

    loc: Sequence[str | int]
    """
    The location of the issue occurrence within the manifest, specified in a
    path-like format.

    The first element is the key of the manifest, and the rest are the keys of
    the nested dictionaries.
    """

    summary: NotRequired[str]
    """
    The summary.
    When not provided, the first sentence of the message will be used.
    """

    msg: str
    """
    The detailed message.

    When multiple lines are used in the message, the framework will automatically
    dedent it. This allows the analyzer to use Python multiline strings without
    concern for indentation.
    """

    input: NotRequired[Any]
    """The input that caused the issue."""

    fix: NotRequired[str | None]
    """The possible fix for the issue."""

    ctx: NotRequired[Any]
    """The additional context."""
