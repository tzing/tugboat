from __future__ import annotations

import collections
import contextlib
import functools
import threading
import typing
from typing import overload

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from typing import Any

    from tugboat.core import Diagnosis


def prepend_loc(
    prefix: Sequence[str | int], iterable: Iterable[Diagnosis]
) -> Iterable[Diagnosis]:
    """Prepend the path to the location of each diagnosis in the iterable."""

    def _prepend(diagnoses: Diagnosis) -> Diagnosis:
        diagnoses["loc"] = (*prefix, *diagnoses.get("loc", []))
        return diagnoses

    return map(_prepend, iterable)


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


class LruDict[TK, TV](collections.OrderedDict[TK, TV]):
    """A dict that implements LRU cache"""

    def __init__(self, max_size=128):
        super().__init__()
        self.max_size = max_size
        self._lock = threading.RLock()

    def __getitem__(self, key: TK) -> TV:
        with self._lock:
            value = super().__getitem__(key)
            self.move_to_end(key)
            return value

    def __setitem__(self, key: TK, value: TV) -> None:
        with self._lock:
            super().__setitem__(key, value)
            self.move_to_end(key)
            if len(self) > self.max_size:
                first = next(iter(self))
                self.__delitem__(first)

    def __delitem__(self, key: TK) -> None:
        with self._lock:
            super().__delitem__(key)

    @overload
    def get(self, key: TK) -> TV | None: ...
    @overload
    def get(self, key: TK, default: TV) -> TV: ...
    @overload
    def get[T](self, key: TK, default: T) -> TV | T: ...

    def get[T](self, key: TK, default: T | None = None) -> TV | T | None:
        try:
            return self[key]
        except KeyError:
            return default
