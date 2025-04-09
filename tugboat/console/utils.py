from __future__ import annotations

import functools
import io
import sys
import typing

from tugboat.types import PathLike

if typing.TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import TextIO


def format_loc(loc: Sequence[str | int]) -> str:
    return "." + ".".join(map(str, loc))


class CachedStdin(PathLike):
    """A virtual path that reads from stdin and caches the content."""

    def __init__(self):
        super().__init__("<stdin>")

    @property
    def name(self) -> str:
        return "<stdin>"

    def is_file(self) -> bool:
        return True

    def is_dir(self) -> bool:
        return False

    @functools.cache  # noqa: B019; this class should be singleton
    def read_text(self) -> str:
        return sys.stdin.read()

    def open(self, mode: str = "r") -> TextIO:
        if "r" not in mode:
            return NotImplemented  # pragma: no cover
        return io.StringIO(self.read_text())
