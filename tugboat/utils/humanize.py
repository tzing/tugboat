"""
Helper functions for generating human readable text.
"""

from __future__ import annotations

import contextlib
import functools
import io
import typing

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence
    from typing import Any

    from pydantic import BaseModel


def join_items(
    items: Iterable[Any],
    *,
    separator: str = ", ",
    conjunction: str = "and",
    stringify: Callable[[Any], str] = str,
) -> str:
    """
    Join items with a separator. The last item is preceded by a conjunction.

    This function serves as the foundation for the :py:func:`join_with_and` and
    :py:func:`join_with_or` functions.
    """
    iterator = iter(items)

    with io.StringIO() as buffer:
        # join items with the specified separator
        last_item = None
        for item in iterator:
            if buffer.tell():
                buffer.write(separator)
            if last_item is not None:
                buffer.write(stringify(last_item))
            last_item = item

        # special case: empty input
        if last_item is None:
            return "(none)"

        # the last item is joined with the conjunction text
        if buffer.tell():
            buffer.write(f" {conjunction} ")
        if last_item is not None:
            buffer.write(stringify(last_item))

        return buffer.getvalue()


def join_with_and(items: Iterable[Any], *, quote: bool = True) -> str:
    """
    Join items with a comma and the word "and" before the last item.
    """
    return join_items(
        items,
        conjunction="and",
        stringify=_quote if quote else str,
    )


def join_with_or(items: Iterable[Any], *, quote: bool = True) -> str:
    """
    Join items with a comma and the word "or" before the last item.
    """
    return join_items(
        items,
        last_joiner="or",
        stringify=_quote if quote else str,
    )


def join(
    items: Iterable[str],
    *,
    separator: str = ", ",
    last_joiner: str = ", ",
):
    """
    Join items with a separator, with a different last joiner.

    Arguments
    ---------
    items : Iterable[str]
        The items to join.

    Keyword Arguments
    -----------------
    separator : str
        The separator to use between items, by default ``, ``.
    last_joiner : str
        The string to use before the last item.

    Returns
    -------
    str
        The joined string.
    """
    with io.StringIO() as buf:
        # join items with the specified separator
        last_item = None
        for item in iter(items):
            if buf.tell():
                buf.write(separator)
            if last_item is not None:
                buf.write(last_item)
            last_item = item

        # perform the last join
        if buf.tell():
            buf.write(last_joiner)
        if last_item is not None:
            buf.write(last_item)

        return buf.getvalue()


def _quote(item: Any) -> str:
    text = str(item)
    if "'" in text:
        return f'"{text}"'
    return f"'{text}'"


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
    field = type(model).model_fields[name]
    return field.alias or name
