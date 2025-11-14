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

.. tip::

   The ``loc`` parameter provides a convenient way to specify the location
   context without needing to wrap constraint functions with :func:`~tugboat.utils.prepend_loc`.
"""

from __future__ import annotations

import functools
import io
import typing

from tugboat.types import Field
from tugboat.utils import get_context_name, join_with_and, join_with_or

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
            alias = _alias(model, name)
            here = _here("under", loc)
            yield {
                "type": "failure",
                "code": "M102",
                "loc": (*loc, alias),
                "summary": f"Unexpected field '{alias}'",
                "msg": f"Field '{alias}' is not allowed {here}. Remove it.",
                "input": Field(alias),
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
            return  # no issue :)

        case 0 if require_one:
            required_fields = map(functools.partial(_alias, model), fields)
            here = _here("in", loc)
            yield {
                "type": "failure",
                "code": "M101",
                "loc": tuple(loc),
                "summary": "Missing required field",
                "msg": (
                    f"""
                    Missing required field {here}.
                    Set either one of these fields: {join_with_or(required_fields)}.
                    """
                ),
            }

        case _:
            conflicting_fields = map(functools.partial(_alias, model), active_fields)
            message = f"""
                Found multiple mutually exclusive fields set {_here("in", loc)}.
                These fields cannot be used at the same time: {join_with_and(conflicting_fields)}
                """
            for name in active_fields:
                field_alias = _alias(model, name)
                yield {
                    "type": "failure",
                    "code": "M201",
                    "loc": (*loc, field_alias),
                    "summary": "Conflicting fields",
                    "msg": message,
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
            field_alias = _get_alias(model, name)
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
            field_alias = _get_alias(model, name)
            context_name = get_context_name(loc)
            yield {
                "type": "failure",
                "code": "M202",
                "loc": (*loc, field_alias),
                "summary": f"Missing input in field '{field_alias}'",
                "msg": f"Field '{field_alias}' is required in {context_name} but is currently empty.",
            }


def _alias(model: BaseModel, name: str) -> str:
    """Get the alias of a field in a pydantic model."""
    field = type(model).model_fields[name]
    return field.alias or name


def _here(conj: str, loc: Sequence[str | int], default: str = "here") -> str:
    """
    Convert the location tuple into human-readable string.

    Outputs:

    * () -> "here"
    * ("spec", 0, "foo") -> "under @.spec[].foo"
    """
    if not loc:
        return default

    with io.StringIO() as buf:
        buf.write(f"{conj} @")

        for part in loc:
            if isinstance(part, int):
                buf.write("[]")
            else:
                buf.write(f".{part}")
        return buf.getvalue()
