from __future__ import annotations

import re
import typing

from dirty_equals import DirtyEquals, IsDict
from pydantic import BaseModel

if typing.TYPE_CHECKING:
    from typing import Any


class ContainsSubStrings(DirtyEquals[str]):
    def __init__(self, *text: str):
        self.texts = text

    def equals(self, other: Any) -> bool:
        return all(text in other for text in self.texts)


class IsMatch(DirtyEquals[str]):

    def __init__(self, pattern: str):
        super().__init__()
        self.pattern = re.compile(pattern)

    def equals(self, other: Any) -> bool:
        if isinstance(other, str):
            return bool(self.pattern.search(other))
        return False


class IsPartialModel(DirtyEquals[BaseModel]):

    def __init__(self, *args, **kwargs):
        """
        Parameters
        ----------
        fields : Any
            key-value pairs of field-value to check for.
        """
        super().__init__()
        self._expected = dict(*args, **kwargs)

    def equals(self, other):
        if isinstance(other, BaseModel):
            other = other.model_dump()
            return other == IsDict(self._expected).settings(partial=True)
        return False
