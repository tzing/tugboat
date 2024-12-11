from __future__ import annotations

import functools
import io
import typing
from pathlib import Path

if typing.TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import TextIO


def format_loc(loc: Sequence[str | int]) -> str:
    return "." + ".".join(map(str, loc))


class VirtualPath:
    """
    A :py:class:`pathlib.Path`-like object that wraps a stream and mimics the
    behavior of a file on disk.

    It could be used to represent files that are read from standard input or
    generated on the fly.
    """

    def __init__(self, name: str, stream: TextIO):
        self.name = name
        self._stream = stream

    def __fspath__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"VirtualPath({self.name!r})"

    @functools.cache
    def read_text(self) -> str:
        return self._stream.read()

    def open(self, mode: str = "r") -> TextIO:
        if "r" not in mode:
            return NotImplemented
        return io.StringIO(self.read_text())


@functools.lru_cache()
def cached_read(path: Path) -> str:
    """
    Read the content of a file and cache it.
    """
    return path.read_text()
