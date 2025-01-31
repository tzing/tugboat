"""
Operators that could be used to check or report errors in the data model.
"""

from __future__ import annotations

import collections
import typing
from collections.abc import Sequence

from pydantic import BaseModel

from tugboat.parsers import parse_template, report_syntax_errors

if typing.TYPE_CHECKING:
    from collections.abc import Container, Iterable, Iterator

    from tugboat.references.context import ReferenceCollection
    from tugboat.schemas import Artifact, Parameter, Template
    from tugboat.types import Diagnosis

    type NamedModel = Artifact | Parameter | Template


def prepend_loc(
    prefix: Sequence[str | int], iterable: Iterable[Diagnosis]
) -> Iterator[Diagnosis]:
    """Prepend the path to the location of each diagnosis in the iterable."""

    def _prepend(diagnoses: Diagnosis) -> Diagnosis:
        diagnoses["loc"] = (*prefix, *diagnoses.get("loc", []))
        return diagnoses

    return map(_prepend, iterable)


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
        if ref not in references:
            closest = references.find_closest(ref)
            yield {
                "code": "VAR002",
                "loc": (),
                "summary": "Invalid reference",
                "msg": f"The used reference '{".".join(ref)}' is invalid.",
                "input": str(node),
                "fix": node.format(closest),
                "ctx": {
                    "ref": ref,
                    "closest": closest,
                },
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
