from __future__ import annotations

__all__ = [
    "join_with_and",
    "join_with_or",
]

import contextlib
import functools
import typing

from tugboat.utils.humanize import join_with_and, join_with_or

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from typing import Any

    from pydantic import BaseModel

    from tugboat.types import Diagnosis


def prepend_loc(
    prefix: Sequence[str | int], iterable: Iterable[Diagnosis]
) -> Iterable[Diagnosis]:
    """Prepend the path to the location of each diagnosis in the iterable."""

    def _prepend(diagnoses: Diagnosis) -> Diagnosis:
        diagnoses["loc"] = (*prefix, *diagnoses.get("loc", []))
        return diagnoses

    return map(_prepend, iterable)


def get_context_name(loc: Sequence[str | int]) -> str:
    """Get the parent context name for a location."""
    if not isinstance(loc, tuple):
        loc = tuple(loc)
    return _get_context_name(loc)


@functools.lru_cache(16)
def _get_context_name(loc: tuple[str | int, ...]) -> str:
    with contextlib.suppress(StopIteration):
        # find the first string in the parents
        parent = next(filter(lambda x: isinstance(x, str), reversed(loc)))
        return f"the '{parent}' section"
    return "current context"


def get_alias(model: BaseModel, name: str) -> str:
    """Get the alias of a field in a model."""
    field = model.model_fields[name]
    return field.alias or name
