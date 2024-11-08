from __future__ import annotations

import contextlib
import functools
import typing

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from typing import Any

    from tugboat.core import Diagnostic


def prepend_loc(
    prefix: Sequence[str | int], iterable: Iterable[Diagnostic]
) -> Iterable[Diagnostic]:
    """Decorator to prepend the location prefix to the issue."""
    _prepend = functools.partial(_prepend_loc, prefix=prefix)
    return map(_prepend, iterable)


def _prepend_loc(diagnostic: Diagnostic, prefix: Sequence[str | int]) -> Diagnostic:
    """The helper function to prepend the location prefix to the diagnostic."""
    diagnostic["loc"] = (*prefix, *diagnostic.get("loc", []))
    return diagnostic


def join_items(
    items: Sequence[Any],
    *,
    quote: bool = True,
    separator: str = ", ",
    conjunction: str = "and",
) -> str:
    """Join items with a separator."""
    if quote:
        items = [f"'{item}'" for item in items]
    if len(items) == 1:
        return items[0]
    items, last = items[:-1], items[-1]
    return separator.join(items) + f" {conjunction} {last}"


join_with_and = functools.partial(join_items, conjunction="and")
join_with_or = functools.partial(join_items, conjunction="or")


def get_context_name(loc: Sequence[str | int]) -> str:
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