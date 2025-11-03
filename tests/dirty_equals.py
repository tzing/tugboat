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
        self.pattern = re.compile(pattern)
        super().__init__(self.pattern.pattern)

    def equals(self, other: Any) -> bool:
        if not isinstance(other, str):
            return False
        if not self.pattern.search(other):
            return False
        return True


class HasSubstring(IsMatch):

    def __init__(self, substring: str):
        super().__init__(re.escape(substring))


class IsPartialModel(DirtyEquals[BaseModel]):

    def __init__(self, *args, **kwargs):
        """
        Parameters
        ----------
        fields : Any
            key-value pairs of field-value to check for.
        """
        super().__init__(**dict(*args, **kwargs))

    def equals(self, other):
        if isinstance(other, BaseModel):
            other = other.model_dump()
            return other == IsDict(self._repr_kwargs).settings(partial=True)
        return False
