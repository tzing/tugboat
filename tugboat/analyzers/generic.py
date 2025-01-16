from __future__ import annotations

import collections
import typing

from pydantic import BaseModel

from tugboat.parsers import parse_template, report_syntax_errors
from tugboat.utils import prepend_loc

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from tugboat.references.context import ReferenceCollection
    from tugboat.schemas import Artifact, Parameter, Template
    from tugboat.types import Diagnosis

    type NamedModel = Artifact | Parameter | Template
    type DocumentMap = dict[tuple[str | int, ...], str]


def report_duplicate_names(items: Sequence[NamedModel]) -> Iterator[tuple[int, str]]:
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


def check_argo_variable_errors(
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
        The reference collection for the current context.

    Yields
    ------
    """
    # collect all the fields that are strings
    sources: DocumentMap = {}

    def _check(model: BaseModel, loc: tuple[str | int, ...] = ()):
        for field, value in model:
            if isinstance(value, str):
                sources[*loc, field] = value
            if isinstance(value, BaseModel):
                _check(value, (*loc, field))
            if isinstance(value, list):
                for idx, item in enumerate(value):
                    if isinstance(item, BaseModel):
                        _check(item, (*loc, field, idx))

    _check(model)

    # check templates
    for loc, value in sources.items():
        doc = parse_template(value)
        yield from prepend_loc(loc, report_syntax_errors(doc))

        for node, ref in doc.iter_references():
            if ref not in references:
                closest = references.find_closest(ref)
                yield {
                    "code": "VAR002",
                    "loc": loc,
                    "summary": "Invalid reference",
                    "msg": f"The used reference '{".".join(ref)}' is invalid.",
                    "input": str(node),
                    "fix": node.format(closest),
                }
