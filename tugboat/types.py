from __future__ import annotations

import glob
import os
import re
import typing
from pathlib import Path
from typing import TypedDict

import pydantic_core.core_schema

import tugboat._vendor.glob

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from typing import Any, Literal, NotRequired

    from pydantic import GetCoreSchemaHandler
    from pydantic_core import CoreSchema


class Diagnosis(TypedDict):
    """
    A diagnosis reported by the analyzer.

    This class is a :py:class:`~typing.TypedDict` that defines the structure of
    a diagnosis produced by the analyzer. It serves as the standard format for
    reporting issues detected during analysis.

    All analyzers return diagnoses in this format to ensure consistency across
    different implementations.
    """

    type: NotRequired[Literal["error", "failure", "warning"]]
    """
    The diagnosis type.
    When not provided, it defaults to "failure".

    * ``error`` indicates a critical issue that prevents the analyzer from running.
    * ``failure`` indicates an issue that the analyzer has detected.
    * ``warning`` indicates a potential issue that the analyzer has detected.
      This is not a critical issue, but it may require attention.
    """

    code: str
    """A unique identifier representing the violated rule."""

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
    """Possible fix for the issue."""

    ctx: NotRequired[Any]
    """Additional context."""


class AugmentedDiagnosis(TypedDict):
    """
    The augmented diagnosis reported by the analyzer.

    This type extends the :py:class:`Diagnosis` and adds additional fields
    to provide more context about the diagnosis.
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


class PathLike:
    """
    A base class that implements the :py:class:`os.PathLike` interface and works
    with :py:mod:`pydantic` for serialization and deserialization.
    """

    def __init__(self, representation: str):
        self._representation = representation

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:

        def _validator(v: Any):
            if isinstance(v, str):
                v = cls(v)
            return v

        python_schema = pydantic_core.core_schema.no_info_before_validator_function(
            _validator, pydantic_core.core_schema.is_instance_schema(cls)
        )
        json_schema = pydantic_core.core_schema.no_info_after_validator_function(
            str, pydantic_core.core_schema.str_schema()
        )
        return pydantic_core.core_schema.json_or_python_schema(
            python_schema=python_schema,
            json_schema=json_schema,
            serialization=pydantic_core.core_schema.to_string_ser_schema(),
        )

    def __fspath__(self) -> str:
        return self._representation

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._representation!r})"

    def __str__(self) -> str:
        return self._representation


class GlobPath(PathLike):
    """Wraps a glob pattern for path matching."""

    def __init__(self, pattern: str | os.PathLike):
        pattern = str(pattern)
        if "*" not in pattern and "?" not in pattern:
            raise ValueError(f"Pattern '{pattern}' is not a glob pattern")

        pattern = os.path.realpath(pattern)
        super().__init__(pattern)

        regex_pattern = tugboat._vendor.glob.translate(
            pattern, recursive=True, include_hidden=True
        )
        self._regex_pattern = re.compile(regex_pattern)

    def __eq__(self, value) -> bool:
        if isinstance(value, GlobPath):
            value = str(value)
        path = os.path.realpath(value)
        return self._regex_pattern.match(path) is not None

    def iglob(
        self,
        *,
        recursive: bool = False,
        include_hidden: bool = False,
    ) -> Iterator[Path]:
        """Iterate over the files that match the pattern."""
        for item in glob.iglob(
            self._representation,
            recursive=recursive,
            include_hidden=include_hidden,
        ):
            yield Path(item)


class Field(str):
    """
    Representing a field in a YAML document.

    This class is tended to be used as :py:attr:`Diagnosis.input` to indicate
    that the diagnosis is related to a specific field in the YAML document.
    """
