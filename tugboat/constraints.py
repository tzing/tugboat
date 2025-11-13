"""
This module provides some generic constraints that can be used on linting models.

All functions in this module are generators that yield :py:class:`~tugboat.Diagnosis`
objects when a constraint is not met. These functions can be used in analysis
hooks, yielding results using the :py:keyword:`yield from <yield>` syntax.

A typical usage of these functions is as follows:

.. code-block:: python

   from tugboat import hookimpl
   from tugboat.constraints import mutually_exclusive

   @hookimpl
   def analyze_workflow(workflow: Workflow) -> Iterator[Diagnosis]:
       yield from mutually_exclusive(
           workflow.metadata,
           fields=["name", "generateName"],
           loc=("metadata",),
           require_one=True,
       )
"""

from __future__ import annotations

import functools
import typing

from tugboat.types import Field
from tugboat.utils import get_alias, get_context_name, join_with_and, join_with_or

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

    from pydantic import BaseModel

    from tugboat.types import Diagnosis


def accept_none(
    model: BaseModel,
    *,
    fields: Iterable[str],
    loc: Sequence[str | int] = (),
) -> Iterator[Diagnosis]:
    """
    Check if all the specified fields are not set.

    Parameters
    ----------
    model : BaseModel
        The model to check.
    fields : Iterable[str]
        The attributes that should not be set.
    loc : Sequence[str | int]
        The location prefix for the reported diagnosis.

    Yield
    -----
    :rule:`m102` for each unexpected field.
    """
    for name in fields:
        if getattr(model, name, None) is not None:
            field_alias = get_alias(model, name)
            yield {
                "type": "failure",
                "code": "M102",
                "loc": (*loc, field_alias),
                "summary": f"Found redundant field '{field_alias}'",
                "msg": f"Field '{field_alias}' is not valid within {get_context_name(loc)}.",
                "input": Field(field_alias),
            }


def mutually_exclusive(
    model: BaseModel,
    *,
    fields: Iterable[str],
    loc: Sequence[str | int] = (),
    require_one: bool = False,
) -> Iterator[Diagnosis]:
    """
    Ensures that at most one of the specified fields in the model is set, but
    does not require any of them to be set.

    Parameters
    ----------
    model : BaseModel
        The model to check.
    fields : Iterable[str]
        The attributes that are mutually exclusive.
    loc : Sequence[str | int]
        The location prefix for the reported diagnosis.
    require_one : bool
        Whether exactly one field is required to be set.

    Yield
    -----
    :rule:`m101` when none of the fields are set, if ``require_one`` is :obj:`True`.
    :rule:`m201` when more than one were set.
    """
    active_fields = []
    for name in fields:
        if getattr(model, name, None) is not None:
            active_fields.append(name)

    match len(active_fields):
        case 1:
            return  # no issues :)

        case 0 if require_one:
            required_fields = map(functools.partial(get_alias, model), fields)
            yield {
                "type": "failure",
                "code": "M101",
                "loc": tuple(loc),
                "summary": "Missing required field",
                "msg": (
                    f"""
                    Missing required field for {get_context_name(loc)}.
                    One of the following fields is required: {join_with_or(required_fields)}.
                    """
                ),
            }

        case _:
            conflicting_fields = map(functools.partial(get_alias, model), fields)
            conflicting_fields = join_with_and(conflicting_fields)
            for name in active_fields:
                field_alias = get_alias(model, name)
                yield {
                    "type": "failure",
                    "code": "M201",
                    "loc": (*loc, field_alias),
                    "summary": "Mutually exclusive field set",
                    "msg": f"Field {conflicting_fields} are mutually exclusive.",
                    "input": Field(field_alias),
                }


def require_all(
    model: BaseModel,
    *,
    fields: Iterable[str],
    loc: Sequence[str | int] = (),
    accept_empty: bool = False,
) -> Iterator[Diagnosis]:
    """
    Requires that all of the specified fields in the model are set.

    Parameters
    ----------
    model : BaseModel
        The model to check.
    fields : Iterable[str]
        The attributes that are required.
    loc : Sequence[str | int]
        The location prefix for the reported diagnosis.
    accept_empty : bool
        Whether empty values (e.g., empty strings, empty lists) are accepted
        as valid input.

    Yield
    -----
    :rule:`m101` when any of the fields are absent.
    :rule:`m202` when any of the fields are empty, only if ``accept_empty`` is :obj:`False`.
    """
    for name in fields:
        # early exit if value is set
        if value := getattr(model, name, None):
            continue

        # field absent
        if value is None:
            field_alias = get_alias(model, name)
            context_name = get_context_name(loc)
            yield {
                "type": "failure",
                "code": "M101",
                "loc": (*loc, field_alias),
                "summary": f"Missing required field '{field_alias}'",
                "msg": f"Field '{field_alias}' is required in {context_name} but missing.",
            }

        # field empty
        elif not accept_empty:
            field_alias = get_alias(model, name)
            context_name = get_context_name(loc)
            yield {
                "type": "failure",
                "code": "M202",
                "loc": (*loc, field_alias),
                "summary": f"Missing input in field '{field_alias}'",
                "msg": f"Field '{field_alias}' is required in {context_name} but is currently empty.",
            }
