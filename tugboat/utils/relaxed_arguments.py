"""
This module provides helper functions to create error messages and hints for
incorrect usage of workflow arguments.

It is designed to work with the :py:class:`tugboat.schemas.arguments.RelaxedArguments`
schema and helps users identify and correct mistakes in argument usage.
"""

from __future__ import annotations

import json
import textwrap
import typing

from tugboat.utils.pydantic import get_type_name

if typing.TYPE_CHECKING:
    from collections.abc import Iterator

    from tugboat.schemas.arguments import RelaxedArtifact, RelaxedParameter
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


def critique_relaxed_artifact(artifact: RelaxedArtifact) -> Iterator[Diagnosis]:
    """
    Check for common mistakes in artifact definitions.

    This function works with :py:class:`~tugboat.schemas.arguments.artifact.RelaxedArtifact`
    to identify common issues in :py:class:`~tugboat.schemas.Artifact`
    and provides clearer, more user-friendly error messages.

    Parameters
    ----------
    artifact : RelaxedArtifact
        The artifact to check.

    Yields
    ------
    :rule:`M102` for redundant field in the artifact definition.
    """
    if artifact.value is not None:
        # serialize value to string
        value = artifact.value
        if isinstance(value, bool | int | dict | list):
            try:
                value = json.dumps(value, indent=2)
            except Exception:
                ...

        # build raw artifact expression
        raw_artifact = None
        if isinstance(value, str):
            if "\n" in value:
                # multiple lines
                data = textwrap.indent(value, "    ")
                raw_artifact = f"raw:\n  data: |-\n{data}"
            else:
                # single line
                data = json.dumps(value)
                raw_artifact = f"raw:\n  data: {data}"

        yield {
            "type": "failure",
            "code": "M102",
            "loc": ("value",),
            "summary": "Found redundant field",
            "msg": (
                """
                Field 'value' is not a valid field for artifact.
                If a literal value is intended, use raw artifact instead.
                """
            ),
            "input": "value",
            "fix": raw_artifact,
        }
