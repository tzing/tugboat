from __future__ import annotations

import collections
import typing
from collections.abc import Mapping, Sequence

from rapidfuzz.process import extractOne

from tugboat.utils.humanize import get_context_name, join_with_or

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from typing import Any

    from pydantic_core import ErrorDetails

    from tugboat.types import Diagnosis


def bulk_translate_pydantic_errors(
    errors: Iterable[ErrorDetails],
) -> list[Diagnosis]:
    """
    Translate multiple Pydantic errors to diagnosis objects.

    This function helps to translate multiple Pydantic errors to diagnosis objects,
    and merges some of the similar errors into a more concise message.

    See :func:`translate_pydantic_error` for the details of the translation.

    Parameters
    ----------
    errors : ~collections.abc.Iterable[~pydantic_core.ErrorDetails]
        An iterable of Pydantic error objects. These objects could be obtained from
        :py:meth:`ValidationError.errors <pydantic_core.ValidationError.errors>` method.

    Yields
    ------
    list[Diagnosis]
        A list of diagnosis objects that contain the error messages
    """
    diagnoes = []

    # for union types, pydantic raises multiple errors for the same field
    # so handle them separately

    def _is_union_type_error(err: ErrorDetails, tp: str) -> bool:
        """
        filter error related to union types

        we observed that pydantic appends the type name to the 'loc' for union type:

        ```json
        {
            "type": "int_type",
            "loc": ["foo", "bar", "int"],
            "msg": "Input should be a valid integer"
        }
        ```
        """
        return err["loc"][-1] == tp and (
            err["type"] == f"{tp}_type" or err["type"] == f"{tp}_parsing"
        )

    union_errors = collections.defaultdict(list)
    for err in errors:
        if (
            False
            or _is_union_type_error(err, "bool")
            or _is_union_type_error(err, "bytes")
            or _is_union_type_error(err, "date")
            or _is_union_type_error(err, "datetime")
            or _is_union_type_error(err, "decimal")
            or _is_union_type_error(err, "dict")
            or _is_union_type_error(err, "float")
            or _is_union_type_error(err, "frozen_set")
            or _is_union_type_error(err, "int")
            or _is_union_type_error(err, "iterable")
            or _is_union_type_error(err, "json")
            or _is_union_type_error(err, "list")
            or _is_union_type_error(err, "mapping")
            or _is_union_type_error(err, "set")
            or _is_union_type_error(err, "time_delta")
            or _is_union_type_error(err, "time")
            or _is_union_type_error(err, "tuple")
            or _is_union_type_error(err, "url")
            or _is_union_type_error(err, "uuid")
        ):
            union_errors[err["loc"][:-1]].append(err)

        elif err["type"] == "string_type" and err["loc"][-1] == "str":  # :,)
            union_errors[err["loc"][:-1]].append(err)

        else:
            # other errors - yield as is
            diagnoes.append(translate_pydantic_error(err))

    # merge union type errors
    for loc, errors in union_errors.items():
        # collect all expected types
        expected_types = {err["loc"][-1] for err in errors}
        expected_type_expr = join_with_or(sorted(expected_types), quote=False)

        # build a more concise message
        _, field = _get_field_name(loc)
        input_type = get_type_name(errors[0]["input"])

        diagnoes.append(
            {
                "type": "failure",
                "code": "M007",
                "loc": loc,
                "summary": "Input type mismatch",
                "msg": (
                    f"Expected {expected_type_expr} for field {field}, but received a {input_type}."
                ),
                "input": errors[0]["input"],
            }
        )

    return diagnoes


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
        * - `dict_type <https://docs.pydantic.dev/latest/errors/validation_errors/#dict_type>`_
          - :ref:`code.m007`
        * - `decimal_parsing <https://docs.pydantic.dev/latest/errors/validation_errors/#decimal_parsing>`_
          - :ref:`code.m007`
        * - `decimal_type <https://docs.pydantic.dev/latest/errors/validation_errors/#decimal_type>`_
          - :ref:`code.m007`
        * - `enum <https://docs.pydantic.dev/latest/errors/validation_errors/#enum>`_
          - :ref:`code.m008`
        * - `extra_forbidden <https://docs.pydantic.dev/latest/errors/validation_errors/#extra_forbidden>`_
          - :ref:`code.m005`
        * - `float_parsing <https://docs.pydantic.dev/latest/errors/validation_errors/#float_parsing>`_
          - :ref:`code.m007`
        * - `float_type <https://docs.pydantic.dev/latest/errors/validation_errors/#float_type>`_
          - :ref:`code.m007`
        * - `frozen_set_type <https://docs.pydantic.dev/latest/errors/validation_errors/#frozen_set_type>`_
          - :ref:`code.m007`
        * - `int_parsing <https://docs.pydantic.dev/latest/errors/validation_errors/#int_parsing>`_
          - :ref:`code.m007`
        * - `int_type <https://docs.pydantic.dev/latest/errors/validation_errors/#int_type>`_
          - :ref:`code.m007`
        * - `iterable_type <https://docs.pydantic.dev/latest/errors/validation_errors/#iterable_type>`_
          - :ref:`code.m007`
        * - `list_type <https://docs.pydantic.dev/latest/errors/validation_errors/#list_type>`_
          - :ref:`code.m007`
        * - `literal_error <https://docs.pydantic.dev/latest/errors/validation_errors/#literal_error>`_
          - :ref:`code.m008`
        * - `mapping_type <https://docs.pydantic.dev/latest/errors/validation_errors/#mapping_type>`_
          - :ref:`code.m007`
        * - `missing <https://docs.pydantic.dev/latest/errors/validation_errors/#missing>`_
          - :ref:`code.m004`
        * - `set_type <https://docs.pydantic.dev/latest/errors/validation_errors/#set_type>`_
          - :ref:`code.m007`
        * - `string_type <https://docs.pydantic.dev/latest/errors/validation_errors/#string_type>`_
          - :ref:`code.m007`
        * - `tuple_type <https://docs.pydantic.dev/latest/errors/validation_errors/#tuple_type>`_
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
        case "bool_parsing" | "bool_type":
            _, field = _get_field_name(error["loc"])
            input_type = get_type_name(error["input"])
            return {
                "type": "failure",
                "code": "M007",
                "loc": error["loc"],
                "summary": "Input should be a valid boolean",
                "msg": (
                    f"Expected a boolean for field {field}, but received a {input_type}.\n"
                    "Try using 'true' or 'false' without quotes."
                ),
                "input": error["input"],
            }

        case "dict_type" | "mapping_type":
            _, field = _get_field_name(error["loc"])
            input_type = get_type_name(error["input"])

            if not error["input"]:
                return {
                    "type": "failure",
                    "code": "M007",
                    "loc": error["loc"],
                    "summary": "Input should be a valid mapping",
                    "msg": (
                        f"Expected a mapping for field {field}, but received a {input_type}.\n"
                        "If an empty mapping is intended, use '{}'."
                    ),
                    "input": error["input"],
                    "fix": "{}",
                }

            return {
                "type": "failure",
                "code": "M007",
                "loc": error["loc"],
                "summary": "Input should be a valid mapping",
                "msg": f"Expected a mapping for field {field}, but received a {input_type}.",
                "input": error["input"],
            }

        case "decimal_parsing" | "decimal_type" | "float_parsing" | "float_type":
            _, field = _get_field_name(error["loc"])
            input_type = get_type_name(error["input"])
            return {
                "type": "failure",
                "code": "M007",
                "loc": error["loc"],
                "summary": "Input should be a valid floating point number",
                "msg": f"Expected a floating point number for field {field}, but received a {input_type}.",
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
                "msg": (
                    f"Input '{input_}' is not a valid value for field {field}.\n"
                    f"Expected {expected_literal}."
                ),
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

        case (
            "frozen_set_type"
            | "iterable_type"
            | "list_type"
            | "set_type"
            | "tuple_type"
        ):
            _, field = _get_field_name(error["loc"])
            input_type = get_type_name(error["input"])

            if not error["input"]:
                return {
                    "type": "failure",
                    "code": "M007",
                    "loc": error["loc"],
                    "summary": "Input should be a valid array",
                    "msg": (
                        f"Expected an array for field {field}, but received a {input_type}.\n"
                        "If an empty array is intended, use '[]'."
                    ),
                    "input": error["input"],
                    "fix": "[]",
                }

            return {
                "type": "failure",
                "code": "M007",
                "loc": error["loc"],
                "summary": "Input should be a valid array",
                "msg": f"Expected an array for field {field}, but received a {input_type}.",
                "input": error["input"],
            }

        case "int_parsing" | "int_type":
            _, field = _get_field_name(error["loc"])
            input_type = get_type_name(error["input"])
            return {
                "type": "failure",
                "code": "M007",
                "loc": error["loc"],
                "summary": "Input should be a valid integer",
                "msg": f"Expected a integer for field {field}, but received a {input_type}.",
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
            _, field = _get_field_name(error["loc"])
            return {
                "type": "failure",
                "code": "M007",
                "loc": error["loc"],
                "summary": "Input should be a valid string",
                "msg": "\n".join(_compose_string_error_message(field, error["input"])),
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
