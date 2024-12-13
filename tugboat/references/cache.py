from __future__ import annotations

import collections
import copy
import functools
import threading
import typing
from typing import overload

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    from tugboat.references.context import Context


class cache:
    """
    Decorator to cache the results of a function.

    This decorator is like :py:func:`functools.lru_cache`, but it returns a copy
    of the cached value instead of the original value.
    """

    def __init__(self, max_size: int):
        self.max_size = max_size
        self.store = LruDict(max_size=max_size)

    def __call__[**P](self, func: Callable[P, Context]) -> Callable[P, Context]:
        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            assert not kwargs
            if (value := self.store.get(args)) is None:
                self.store[args] = value = func(*args, **kwargs)
            return copy.deepcopy(value)

        return _wrapper


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
