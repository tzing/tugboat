from __future__ import annotations

import io
import typing

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
        self._content = None

    def __fspath__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"VirtualPath({self.name!r})"

    def __str__(self) -> str:
        return self.name

    def read_text(self) -> str:
        if self._content is None:
            self._content = self._stream.read()
        return self._content

    def open(self, mode: str = "r") -> TextIO:
        if "r" not in mode:
            return NotImplemented
        return io.StringIO(self.read_text())
