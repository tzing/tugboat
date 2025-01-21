from __future__ import annotations

from collections.abc import MutableSet

from pydantic import BaseModel, Field, InstanceOf
from rapidfuzz.distance.DamerauLevenshtein import (
    distance as dameau_levenshtein_distance,
)
from rapidfuzz.distance.DamerauLevenshtein import (
    normalized_distance as dameau_levenshtein_normalized_distance,
)

type _TR = tuple[str, ...]
"""Type alias for reference, which is a tuple of strings."""


class _AnyStr(str):
    """An object that matches any string."""

    def __eq__(self, value):
        return isinstance(value, str)

    def __repr__(self):
        return "ANY"

    def __hash__(self):
        return super().__hash__()


AnyStr = _AnyStr(":any:")
"""
A special object that matches any string.
"""


class ReferenceCollection(MutableSet[_TR]):
    """
    A :py:class:`set`-like collection of references, handling the special logic
    of :py:data:`AnyStr`.
    """

    def __init__(self):
        self._static = set()
        self._dynamic = []

    def __iter__(self):
        yield from self._static
        yield from self._dynamic

    def __len__(self):
        return len(self._static) + len(self._dynamic)

    def __contains__(self, item):
        return item in self._static or item in self._dynamic

    def __repr__(self):
        return f'{{{", ".join(repr(item) for item in self)}}}'

    def __deepcopy__(self, memo):
        new = type(self)()
        new._static = self._static.copy()
        new._dynamic = self._dynamic.copy()
        return new

    def __add__(self, other):
        new = type(self)()
        new._static = self._static | other._static
        new._dynamic = self._dynamic + other._dynamic
        return new

    def add(self, value):
        if not isinstance(value, tuple | list):
            raise TypeError("value must be a tuple or a list")
        if any(isinstance(item, _AnyStr) for item in value):
            self._dynamic.append(value)
        else:
            self._static.add(value)

    def discard(self, value):
        raise NotImplementedError

    def find_closest(self, target: _TR) -> _TR:
        """
        Find the closest match for a given reference in a list of reference.
        """
        # NOTE this algorithm is heuristic

        # group the candidates by their distance to the target reference
        distance_grouped_candidates: dict[int, list[_TR]] = {}
        for candidate in self:
            dist = dameau_levenshtein_distance(target, candidate)
            distance_grouped_candidates.setdefault(dist, []).append(candidate)

        # find the closest group
        closest_candidates = []
        if distance_grouped_candidates:
            closest_distance = min(distance_grouped_candidates)
            closest_candidates = distance_grouped_candidates[closest_distance]

        # sort by the distance of each element
        def _calculate_distance(candidate: _TR) -> tuple[float, ...]:
            # calculate the normalized distance for each element
            base_distance = (
                dameau_levenshtein_normalized_distance(a, b)
                for a, b in zip(target, candidate, strict=False)
            )

            if len(target) != len(candidate):
                # if the lengths are different, add a penalty to the distance
                return (*base_distance, 2.0)
            else:
                return tuple(base_distance)

        closest_candidates = sorted(closest_candidates, key=_calculate_distance)

        # return the closest match
        for candidate in closest_candidates:
            # in case the candidate contains `AnyStr`, rebuild it with the target reference
            if any(item is AnyStr for item in candidate):
                if len(target) < len(candidate):
                    continue
                return tuple(
                    a if isinstance(b, _AnyStr) else b
                    for a, b in zip(target, candidate, strict=False)
                )
            return candidate

        return ()


class Context(BaseModel):
    parameters: InstanceOf[ReferenceCollection] = Field(
        default_factory=ReferenceCollection
    )
    artifacts: InstanceOf[ReferenceCollection] = Field(
        default_factory=ReferenceCollection
    )
