"""
Operators that could be used to check or report errors in the data model.
"""

from __future__ import annotations

import collections
import itertools
import typing
from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from tugboat.parsers import parse_template, report_syntax_errors
from tugboat.types import Diagnosis

if typing.TYPE_CHECKING:
    from collections.abc import Container, Iterator
    from typing import Protocol, Self

    from tugboat.references.context import ReferenceCollection

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


def check_value_references(
    value: str, references: ReferenceCollection
) -> Iterator[Diagnosis]:
    """
    Check the given value for errors that are specific to Argo workflows
    variables.

    Parameters
    ----------
    value : str
        The value to check.
    references : ReferenceCollection
        The current active references.

    Yields
    ------
    Diagnosis
        A diagnosis for each error found.
    """
    doc = parse_template(value)
    yield from report_syntax_errors(doc)

    for node, ref in doc.iter_references():
        if ref in references:
            continue

        ref_str = ".".join(ref)
        metadata = {
            "found": ref,
            "found:str": ref_str,
        }

        closest = references.find_closest(ref)
        if closest:
            metadata["closest"] = closest
            metadata["closest:str"] = ".".join(closest)

        yield {
            "code": "VAR002",
            "loc": (),
            "summary": "Invalid reference",
            "msg": f"The used reference '{ref_str}' is invalid.",
            "input": str(node),
            "fix": node.format(closest),
            "ctx": {"reference": metadata},
        }


def check_model_fields_references(
    model: BaseModel, references: ReferenceCollection, *, exclude: Container[str] = ()
) -> Iterator[Diagnosis]:
    """
    Check the fields of the given model for errors that are specific to Argo
    workflows variables.

    Parameters
    ----------
    model : BaseModel
        The model to check. This function will check all fields of the model
        that are of type str.
    references : ReferenceCollection
        The current active references.
    exclude : Container[str]
        The fields to exclude from the check.

    Yields
    ------
    Diagnosis
        A diagnosis for each error found.
    """

    def _check(item):
        if isinstance(item, str):
            yield from check_value_references(item, references)

        elif isinstance(item, BaseModel):
            for field, value in item:
                yield from prepend_loc((field,), _check(value))

        elif isinstance(item, Sequence):
            for idx, child in enumerate(item):
                yield from prepend_loc((idx,), _check(child))

    for field, value in model:
        if field not in exclude:
            yield from prepend_loc((field,), _check(value))
