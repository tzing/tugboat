"""
Helper functions for generating human readable text.
"""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any


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
