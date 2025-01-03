from __future__ import annotations

import typing
from collections.abc import Mapping, Sequence

from rapidfuzz.process import extractOne

from tugboat.utils import get_context_name

if typing.TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any

    from pydantic_core import ErrorDetails

    from tugboat.core import Diagnosis


def translate_pydantic_error(error: ErrorDetails) -> Diagnosis:
    """
    Translate a Pydantic error to a diagnosis object.

    Parameters
    ----------
    error : ErrorDetails
        The Pydantic error object. This object could be obtained from
        :py:meth:`pydantic.ValidationError.errors` object.

    Returns
    -------
    Diagnosis
        The diagnosis object.
    """
    field = error["loc"][-1]

    match error["type"]:
        case "bool_parsing" | "bool_type":
            input_type = get_type_name(error["input"])
            return {
                "type": "failure",
                "code": "M007",
                "loc": error["loc"],
                "summary": "Input should be a valid boolean",
                "msg": f"""
                    Field '{field}' should be a valid boolean, got {input_type}.
                    Try using 'true' or 'false' without quotes.
                    """,
                "input": error["input"],
            }

        case "enum" | "literal_error":
            expected_literal = error.get("ctx", {}).get("expected", "")
            expected = _extract_expects(expected_literal)

            input_ = error["input"]
            fix, _, _ = extractOne(error["input"], expected)

            return {
                "type": "failure",
                "code": "M008",
                "loc": error["loc"],
                "summary": error["msg"],
                "msg": f"""
                    Input '{input_}' is not a valid value for field '{field}'.
                    Expected {expected_literal}.
                    """,
                "input": error["input"],
                "fix": fix,
            }

        case "extra_forbidden":
            *parents, _ = error["loc"]
            return {
                "type": "failure",
                "code": "M005",
                "loc": error["loc"],
                "summary": "Found redundant field",
                "msg": f"Field '{field}' is not valid within {get_context_name(parents)}.",
                "input": field,
            }

        case "int_parsing" | "int_type":
            input_type = get_type_name(error["input"])
            return {
                "type": "failure",
                "code": "M007",
                "loc": error["loc"],
                "summary": "Input should be a valid integer",
                "msg": f"Field '{field}' should be a valid integer, got {input_type}.",
                "input": error["input"],
            }

        case "missing":
            return {
                "type": "failure",
                "code": "M004",
                "loc": error["loc"],
                "summary": "Missing required field",
                "msg": f"Field '{field}' is required but missing",
            }

        case "string_type":
            input_type = get_type_name(error["input"])
            msg = [f"Field '{field}' should be a valid string, got {input_type}."]
            msg += _guess_string_problems(error["input"])
            return {
                "type": "failure",
                "code": "M007",
                "loc": error["loc"],
                "summary": "Input should be a valid string",
                "msg": "\n".join(msg),
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
        return "sequence"
    return type(value).__name__


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


def _guess_string_problems(value: Any):
    """
    Guess the problems with the string input, return a list of suggestions.

    Ref: https://ruudvanasseldonk.com/2023/01/11/the-yaml-document-from-hell
    """
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
