"""
This module provides some generic constraints that can be used on linting models.

All functions in this module are generators that yield :py:class:`tugboat.Diagnosis`
objects when a constraint is not met. These functions can be used in analysis
hooks, yielding results using the :py:keyword:`yield from <yield>` syntax.

A typical usage of these functions is as follows:

.. code-block:: python

   from tugboat import hookimpl
   from tugboat.constraints import require_exactly_one

   @hookimpl
   def analyze_workflow(workflow: Workflow) -> Iterator[Diagnosis]:
       yield from require_exactly_one(
           model=workflow.metadata,
           loc=("metadata",),
           fields=["name", "generateName"],
       )
"""

from __future__ import annotations

import typing

from tugboat.utils import get_context_name, join_with_and, join_with_or

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from typing import Any

    from tugboat.types import Diagnosis


def accept_none(
    *, model: Any, loc: Sequence[str | int], fields: Sequence[str]
) -> Iterator[Diagnosis]:
    """
    Check if all the specified fields are not set.

    Yield
    -----
    :ref:`code.m005` for each unexpected field.
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


def mutually_exclusive(
    *, model: Any, loc: Sequence[str | int], fields: Sequence[str]
) -> Iterator[Diagnosis]:
    """
    Ensures that at most one of the specified fields in the model is set, but
    does not require any of them to be set.

    Yield
    -----
    :ref:`code.m006` when more than one were set.
    """
    fields_with_values = [
        field for field in fields if getattr(model, field, None) is not None
    ]
    if len(fields_with_values) > 1:
        fields_str = join_with_and(fields)
        for field in fields_with_values:
            yield {
                "type": "failure",
                "code": "M006",
                "loc": (*loc, field),
                "summary": "Mutually exclusive field set",
                "msg": f"Field {fields_str} are mutually exclusive.",
                "input": field,
            }


def require_all(
    *, model: Any, loc: Sequence[str | int], fields: Sequence[str]
) -> Iterator[Diagnosis]:
    """
    Requires that all of the specified fields in the model are set.

    Yield
    -----
    :ref:`code.m004` for any of the missing or empty fields.
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
) -> Iterator[Diagnosis]:
    """
    Requires that exactly one of the specified fields in the model is set.

    Yield
    -----
    :ref:`code.m004` when none of the fields are set.
    :ref:`code.m006` when more than one were set.
    """
    # check if any of the fields are set
    any_field_set = False
    for field in fields:
        if getattr(model, field, None) is not None:
            any_field_set = True
            break

    if not any_field_set:
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

    yield from mutually_exclusive(model=model, loc=loc, fields=fields)
