from __future__ import annotations

import collections
import sys

from tugboat.types import PathLike
from tugboat.utils import join_with_and


class Stdin(PathLike):
    """A path-like object that reads from stdin."""

    def __init__(self):
        super().__init__("<stdin>")

    def is_file(self) -> bool:
        return True

    def read_text(self) -> str:
        return sys.stdin.read()


class DiagnosesCounter(collections.Counter):

    def summary(self) -> str:
        parts = []
        if count := self["error"]:
            parts.append(f"{count} errors")
        if count := self["failure"]:
            parts.append(f"{count} failures")
        if count := self["warning"]:
            parts.append(f"{count} warnings")

        if parts:
            summary = join_with_and(parts, quote=False, sort=False)
            return f"Found {summary}"

        return "All passed!"

    def has_any_error(self) -> bool:
        return any((self["error"], self["failure"]))
