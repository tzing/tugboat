"""
This module provides helper functions to create error messages and hints for
incorrect usage of workflow arguments.

It is designed to work with the :py:class:`tugboat.schemas.arguments.RelaxedArguments`
schema and helps users identify and correct mistakes in argument usage.
"""

from __future__ import annotations

import json
import typing

from tugboat.utils.pydantic import get_type_name

if typing.TYPE_CHECKING:
    from collections.abc import Iterator

    from tugboat.schemas.arguments import RelaxedParameter
    from tugboat.types import Diagnosis


def critique_relaxed_parameter(param: RelaxedParameter) -> Iterator[Diagnosis]:
    """
    Check for common mistakes in parameter definitions.

    This function works with :py:class:`~tugboat.schemas.arguments.parameter.RelaxedParameter`
    to identify common issues in :py:class:`~tugboat.schemas.Parameter`
    and provides clearer, more user-friendly error messages.

    Parameters
    ----------
    param : RelaxedParameter
        The parameter to check.

    Yields
    ------
    :rule:`M103` for incorrect types in the value field.
    """
    if param.value is not None:
        if isinstance(param.value, dict | list):
            input_type = get_type_name(param.value)

            try:
                alternative = json.dumps(param.value, indent=2)
                if "\n" not in alternative:
                    alternative = json.dumps(alternative)
            except Exception:
                alternative = None

            yield {
                "type": "failure",
                "code": "M103",
                "loc": ("value",),
                "summary": "Input type mismatch",
                "msg": (
                    f"""
                    Expected string for parameter value, but received a {input_type}.
                    If you want to pass an object, try serializing it to a JSON string.
                    """
                ),
                "input": param.value,
                "fix": alternative,
            }

        elif not isinstance(param.value, bool | int | str):
            input_type = get_type_name(param.value)
            yield {
                "type": "failure",
                "code": "M103",
                "loc": ("value",),
                "summary": "Input type mismatch",
                "msg": (
                    f"Expected string for parameter value, but received a {input_type}."
                ),
                "input": param.value,
            }
