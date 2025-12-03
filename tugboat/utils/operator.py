"""
Operators that could be used to check or report errors in the data model.
"""

from __future__ import annotations

import collections
import itertools
import typing
from collections.abc import Iterable, Sequence

from tugboat.types import Diagnosis

if typing.TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Protocol, Self


    class _NamedModel(Protocol):
        name: str

    class _NullableNamedModel(Protocol):
        name: str | None

    # pyright 1.1 says non-nullable and nullable protocols are incompatible
    type NamedModel = _NamedModel | _NullableNamedModel


class prepend_loc(Iterable[Diagnosis]):
    """Prepend path to the location of each diagnosis in an iterable."""

    def __init__(self, prefix: Sequence[str | int], items: Iterable[Diagnosis] = ()):
        self.prefix = prefix
        self.items = items

    def __call__(self, diagnosis: Diagnosis) -> Diagnosis:
        diagnosis["loc"] = (*self.prefix, *diagnosis.get("loc", []))
        return diagnosis

    def __iter__(self) -> Iterator[Diagnosis]:
        return map(self, self.items)

    @classmethod
    def from_iterables(
        cls, prefix: Sequence[str | int], iterables: Iterable[Iterable[Diagnosis]]
    ) -> Self:
        return cls(prefix, itertools.chain.from_iterable(iterables))


def find_duplicate_names(items: Sequence[NamedModel]) -> Iterator[tuple[int, str]]:
    """Find and yield the indices and names of duplicate items in a sequence."""
    # count the number of times each name appears
    names = collections.defaultdict(list)
    for idx, item in enumerate(items):
        if item.name:  # skip if name is empty
            names[item.name].append(idx)

    # report any names that appear more than once
    for name, indices in names.items():
        if len(indices) > 1:
            for idx in indices:
                yield idx, name
