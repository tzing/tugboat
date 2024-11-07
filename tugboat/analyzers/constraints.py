"""
This module provides some generic constraints that can be used on models.
"""

from __future__ import annotations

import typing

from tugboat.analyzers.utils import get_context_name, join_with_and, join_with_or

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from typing import Any

    from tugboat.core import Diagnostic


def accept_none(
    *, model: Any, loc: Sequence[str | int], fields: Sequence[str]
) -> Iterator[Diagnostic]:
    """
    This constraint checks if all the specified fields are set to None. For each
    field that is not None, error M005 is yielded.
    """
    for field in fields:
        if getattr(model, field, None) is not None:
            yield {
                "type": "failure",
                "code": "M005",
                "loc": (*loc, field),
                "summary": f"Found redundant field '{field}'",
                "msg": f"Field '{field}' is not valid within {get_context_name(loc)}.",
                "input": field,
            }


def require_all(
    *, model: Any, loc: Sequence[str | int], fields: Sequence[str]
) -> Iterator[Diagnostic]:
    """
    This constraint requires that all of the specified fields in the model are set.
    If any of the fields are missing, error M004 is yielded.
    """
    for field in fields:
        value = getattr(model, field, None)
        if value is None:
            yield {
                "type": "failure",
                "code": "M004",
                "loc": (*loc, field),
                "summary": f"Missing required field '{field}'",
                "msg": f"Field '{field}' is required in {get_context_name(loc)} but missing",
            }
        elif value == "":
            yield {
                "type": "failure",
                "code": "M004",
                "loc": (*loc, field),
                "summary": f"Missing required field '{field}'",
                "msg": f"Field '{field}' is required in {get_context_name(loc)} but empty",
            }


def require_exactly_one(
    *, model: Any, loc: Sequence[str | int], fields: Sequence[str]
) -> Iterator[Diagnostic]:
    """
    This constraint requires that exactly one of the specified fields in the
    model is set. If the constraint is not met, following errors are yielded:

    M004:
       When none of the fields are set.
    M006:
       When more than one were set.
    """
    set_fields = [field for field in fields if getattr(model, field, None) is not None]

    match len(set_fields):
        case 0:
            yield {
                "type": "failure",
                "code": "M004",
                "loc": tuple(loc),
                "summary": "Missing required field",
                "msg": f"""
                    Missing required field for {get_context_name(loc)}.
                    One of the following fields is required: {join_with_or(fields)}.
                    """,
            }

        case 1:
            ...  # no error!

        case _:
            set_fields_str = join_with_and(set_fields)
            for field in set_fields:
                yield {
                    "type": "failure",
                    "code": "M006",
                    "loc": (*loc, field),
                    "summary": "Mutually exclusive field set",
                    "msg": f"Field {set_fields_str} are mutually exclusive.",
                    "input": field,
                }
