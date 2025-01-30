from __future__ import annotations

__all__ = [
    "get_alias",
    "get_context_name",
    "join_with_and",
    "join_with_or",
]

import contextlib
import functools
import typing

from tugboat.utils.humanize import (
    join_with_and,
    join_with_or,
    get_context_name,
    get_alias,
)

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
