"""
Helper functions for generating human readable text.
"""

from __future__ import annotations

import contextlib
import functools
import typing

if typing.TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any

    from pydantic import BaseModel


def join_items(
    items: Sequence[Any],
    *,
    quote: bool = True,
    separator: str = ", ",
    conjunction: str = "and",
) -> str:
    """
    Join items with a separator. The last item is preceded by a conjunction.

    This function serves as the foundation for the :py:func:`join_with_and` and
    :py:func:`join_with_or` functions.
    """
    if quote:
        items = [f"'{item}'" for item in items]
    match len(items):
        case 0:
            return "(none)"
        case 1:
            return items[0]
    items, last = items[:-1], items[-1]
    return separator.join(items) + f" {conjunction} {last}"


def join_with_and(items: Sequence[Any], *, quote: bool = True) -> str:
    """
    Join items with a comma and the word "and" before the last item.
    """
    return join_items(items, quote=quote, conjunction="and")


def join_with_or(items: Sequence[Any], *, quote: bool = True) -> str:
    """
    Join items with a comma and the word "or" before the last item.
    """
    return join_items(items, quote=quote, conjunction="or")


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
