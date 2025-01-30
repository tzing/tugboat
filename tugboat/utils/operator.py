from __future__ import annotations

import typing
from collections.abc import Sequence

from pydantic import BaseModel

from tugboat.parsers import parse_template, report_syntax_errors

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from tugboat.references.context import ReferenceCollection
    from tugboat.types import Diagnosis


def prepend_loc(
    prefix: Sequence[str | int], iterable: Iterable[Diagnosis]
) -> Iterator[Diagnosis]:
    """Prepend the path to the location of each diagnosis in the iterable."""

    def _prepend(diagnoses: Diagnosis) -> Diagnosis:
        diagnoses["loc"] = (*prefix, *diagnoses.get("loc", []))
        return diagnoses

    return map(_prepend, iterable)


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
    model: BaseModel, references: ReferenceCollection
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

    yield from _check(model)
