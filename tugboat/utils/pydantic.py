from __future__ import annotations

import typing
from collections.abc import Mapping, Sequence

from rapidfuzz.process import extractOne

from tugboat.utils.humanize import get_context_name

if typing.TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any

    from pydantic_core import ErrorDetails

    from tugboat.types import Diagnosis


def translate_pydantic_error(error: ErrorDetails) -> Diagnosis:
    """
    Translate a Pydantic error to a diagnosis object.

    This function returns a diagnosis object based on the error type found in the input:

    .. list-table::

        * - Pydantic Error Type
          - Tugboat Code
        * - `bool_parsing <https://docs.pydantic.dev/latest/errors/validation_errors/#bool_parsing>`_
          - :ref:`code.m007`
        * - `bool_type <https://docs.pydantic.dev/latest/errors/validation_errors/#bool_type>`_
          - :ref:`code.m007`
        * - `enum <https://docs.pydantic.dev/latest/errors/validation_errors/#enum>`_
          - :ref:`code.m008`
        * - `extra_forbidden <https://docs.pydantic.dev/latest/errors/validation_errors/#extra_forbidden>`_
          - :ref:`code.m005`
        * - `int_parsing <https://docs.pydantic.dev/latest/errors/validation_errors/#int_parsing>`_
          - :ref:`code.m007`
        * - `int_type <https://docs.pydantic.dev/latest/errors/validation_errors/#int_type>`_
          - :ref:`code.m007`
        * - `literal_error <https://docs.pydantic.dev/latest/errors/validation_errors/#literal_error>`_
          - :ref:`code.m008`
        * - `missing <https://docs.pydantic.dev/latest/errors/validation_errors/#missing>`_
          - :ref:`code.m004`
        * - `string_type <https://docs.pydantic.dev/latest/errors/validation_errors/#string_type>`_
          - :ref:`code.m007`
        * - Any other error
          - :ref:`code.m003`

    Parameters
    ----------
    error : ~pydantic_core.ErrorDetails
        A Pydantic error object. This object could be obtained from
        :py:meth:`ValidationError.errors <pydantic_core.ValidationError.errors>` method.

    Returns
    -------
    ~tugboat.types.Diagnosis
       A diagnosis object that contains the error message and other relevant information.
    """
    match error["type"]:
        case "bool_parsing":
            _, field = _get_field_name(error["loc"])
            input_type = get_type_name(error["input"])
            return {
                "type": "failure",
                "code": "M007",
                "loc": error["loc"],
                "summary": "Input should be a valid boolean",
                "msg": f"""
                    Expected a boolean for field {field}, but received a {input_type}.
                    Try using 'true' or 'false' without quotes.
                    """,
                "input": error["input"],
            }

        case "bool_type":
            loc = error["loc"][:-1]  # last item is type name
            _, field = _get_field_name(loc)
            input_type = get_type_name(error["input"])
            return {
                "type": "failure",
                "code": "M007",
                "loc": loc,
                "summary": "Input should be a valid boolean",
                "msg": f"""
                    Expected a boolean for field {field}, but received a {input_type}.
                    Try using 'true' or 'false' without quotes.
                    """,
                "input": error["input"],
            }

        case "enum" | "literal_error":
            expected_literal = error.get("ctx", {}).get("expected", "")
            expected = _extract_expects(expected_literal)

            _, field = _get_field_name(error["loc"])

            input_ = error["input"]
            fix, _, _ = extractOne(error["input"], expected)

            return {
                "type": "failure",
                "code": "M008",
                "loc": error["loc"],
                "summary": error["msg"],
                "msg": f"""
                    Input '{input_}' is not a valid value for field {field}.
                    Expected {expected_literal}.
                    """,
                "input": error["input"],
                "fix": fix,
            }

        case "extra_forbidden":
            raw_field_name, formatted_field = _get_field_name(error["loc"])
            *parents, _ = error["loc"]
            return {
                "type": "failure",
                "code": "M005",
                "loc": error["loc"],
                "summary": "Found redundant field",
                "msg": f"Field {formatted_field} is not valid within {get_context_name(parents)}.",
                "input": raw_field_name,
            }

        case "int_parsing" | "int_type":
            input_type = get_type_name(error["input"])
            return {
                "type": "failure",
                "code": "M007",
                "loc": error["loc"],
                "summary": "Input should be a valid integer",
                "msg": f"Field {field_display} should be a valid integer, got {input_type}.",
                "input": error["input"],
            }

        case "missing":
            _, field = _get_field_name(error["loc"])
            return {
                "type": "failure",
                "code": "M004",
                "loc": error["loc"],
                "summary": "Missing required field",
                "msg": f"Field {field} is required but missing",
            }

        case "string_type":
            return {
                "type": "failure",
                "code": "M007",
                "loc": error["loc"],
                "summary": "Input should be a valid string",
                "msg": "\n".join(
                    _compose_string_error_message(field_display, error["input"])
                ),
                "input": error["input"],
            }

    return {
        "type": "failure",
        "code": "M003",
        "loc": error["loc"],
        "msg": error["msg"],
        "input": error["input"],
        "ctx": {"pydantic_error": error},
    }


def get_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, str):
        return "string"
    if isinstance(value, float):
        return "floating point number"
    if isinstance(value, Mapping):
        return "mapping"
    if isinstance(value, Sequence):
        return "array"
    return type(value).__name__


def _get_field_name(loc: tuple[int | str, ...]) -> tuple[str | None, str]:
    """
    Get the last string in the location tuple as the field name.

    Returns
    -------
    raw : str
        The raw field name.
    quoted : str
        The quoted field name for display.
    """
    for item in reversed(loc):
        if isinstance(item, str):
            return item, f"'{item}'"
    return None, "<unnamed>"


def _extract_expects(literal: str) -> Iterator[str]:
    """
    Extract the expected values from pydantic's error message.

    The expected value string is like:

    .. code-block:: none

       "hello'", 'world' or 'hola'
    """
    idx = 0
    while idx < len(literal):
        if literal[idx] == "'":
            idx_end = literal.find("'", idx + 1)
            yield literal[idx + 1 : idx_end]
            idx = idx_end + 1

        elif literal[idx] == '"':
            idx_end = literal.find('"', idx + 1)
            yield literal[idx + 1 : idx_end]
            idx = idx_end + 1

        else:
            idx += 1


def _compose_string_error_message(field: str, value: Any) -> Iterator[str]:
    """
    Construct an error message for string type validation.
    Includes user suggestions based on the value and common YAML parsing pitfalls.

    Ref: https://ruudvanasseldonk.com/2023/01/11/the-yaml-document-from-hell
    """
    input_type = get_type_name(value)
    yield f"Expected a string for field {field}, but received a {input_type}."

    # the Norway problem
    if isinstance(value, bool):
        if value is True:
            yield "Note that these inputs will be interpreted as boolean true: 'True', 'Yes', 'On', 'Y'."
        else:
            yield "Note that these inputs will be interpreted as boolean false: 'False', 'No', 'Off', 'N'."

    # sexagesimal
    if isinstance(value, int) and 60 < value <= 3600:
        sexagesimal = _to_sexagesimal(value)
        yield (
            f"Numbers separated by colons (e.g. {sexagesimal}) will be interpreted as sexagesimal."
        )

    # general suggestion
    yield "Try using quotes for strings to fix this issue."


def _to_sexagesimal(value: int) -> str:
    """Convert an integer to a sexagesimal string."""
    if value < 0:
        sign = "-"
        value = -value
    else:
        sign = ""

    digits = []
    while value:
        digits.append(value % 60)
        value //= 60

    return sign + ":".join(str(d) for d in reversed(digits))
