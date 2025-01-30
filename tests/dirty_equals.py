from __future__ import annotations

import typing

from dirty_equals import DirtyEquals

if typing.TYPE_CHECKING:
    from typing import Any


class ContainsSubStrings(DirtyEquals[str]):
    def __init__(self, *text: str):
        self.texts = text

    def equals(self, other: Any) -> bool:
        return all(text in other for text in self.texts)
