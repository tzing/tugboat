from __future__ import annotations

import collections
import contextlib
import io
import json
import typing
from collections.abc import Mapping, Sequence

from rapidfuzz.process import extractOne

from tugboat.types import Field
from tugboat.utils.humanize import join_with_or

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from typing import Any

    from pydantic_core import ErrorDetails

    from tugboat.types import Bundle, Diagnosis


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
        expected_type_expr = join_with_or(expected_types, quote=False)

        # build a more concise message
        field = _get_field(loc)
        input_type = get_type_name(errors[0]["input"])

        diagnoes.append(
            {
                "type": "failure",
                "code": "M103",
                "loc": loc,
                "summary": "Input type mismatch",
                "msg": (
                    f"Expected {expected_type_expr} for field '{field}', but received a {input_type}."
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
          - :rule:`m103`
        * - `bool_type <https://docs.pydantic.dev/latest/errors/validation_errors/#bool_type>`_
          - :rule:`m103`
        * - `dict_type <https://docs.pydantic.dev/latest/errors/validation_errors/#dict_type>`_
          - :rule:`m103`
        * - `decimal_parsing <https://docs.pydantic.dev/latest/errors/validation_errors/#decimal_parsing>`_
          - :rule:`m103`
        * - `decimal_type <https://docs.pydantic.dev/latest/errors/validation_errors/#decimal_type>`_
          - :rule:`m103`
        * - `enum <https://docs.pydantic.dev/latest/errors/validation_errors/#enum>`_
          - :rule:`m104`
        * - `extra_forbidden <https://docs.pydantic.dev/latest/errors/validation_errors/#extra_forbidden>`_
          - :rule:`m102`
        * - `float_parsing <https://docs.pydantic.dev/latest/errors/validation_errors/#float_parsing>`_
          - :rule:`m103`
        * - `float_type <https://docs.pydantic.dev/latest/errors/validation_errors/#float_type>`_
          - :rule:`m103`
        * - `frozen_set_type <https://docs.pydantic.dev/latest/errors/validation_errors/#frozen_set_type>`_
          - :rule:`m103`
        * - `int_parsing <https://docs.pydantic.dev/latest/errors/validation_errors/#int_parsing>`_
          - :rule:`m103`
        * - `int_type <https://docs.pydantic.dev/latest/errors/validation_errors/#int_type>`_
          - :rule:`m103`
        * - `iterable_type <https://docs.pydantic.dev/latest/errors/validation_errors/#iterable_type>`_
          - :rule:`m103`
        * - `list_type <https://docs.pydantic.dev/latest/errors/validation_errors/#list_type>`_
          - :rule:`m103`
        * - `literal_error <https://docs.pydantic.dev/latest/errors/validation_errors/#literal_error>`_
          - :rule:`m104`
        * - `mapping_type <https://docs.pydantic.dev/latest/errors/validation_errors/#mapping_type>`_
          - :rule:`m103`
        * - `missing <https://docs.pydantic.dev/latest/errors/validation_errors/#missing>`_
          - :rule:`m101`
        * - `set_type <https://docs.pydantic.dev/latest/errors/validation_errors/#set_type>`_
          - :rule:`m103`
        * - `string_type <https://docs.pydantic.dev/latest/errors/validation_errors/#string_type>`_
          - :rule:`m103`
        * - `tuple_type <https://docs.pydantic.dev/latest/errors/validation_errors/#tuple_type>`_
          - :rule:`m103`
        * - Any other error
          - :rule:`m003`

    Below are some custom error types defined in Tugboat:

    .. list-table::

        * - Custom Error Type
          - Tugboat Code
        * - ``artifact_prohibited_value_field``
          - :rule:`m102`
        * - ``parameter_value_type_error``
          - :rule:`m103`

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
            field = _get_field(error["loc"])
            input_type = get_type_name(error["input"])
            return {
                "type": "failure",
                "code": "M103",
                "loc": error["loc"],
                "summary": "Input should be a valid boolean",
                "msg": (
                    f"Expected a boolean for field '{field}', but received a {input_type}.\n"
                    "Use 'true' or 'false' without quotes for boolean values."
                ),
                "input": error["input"],
            }

        case "dict_type" | "mapping_type":
            field = _get_field(error["loc"])
            input_type = get_type_name(error["input"])

            if not error["input"]:
                return {
                    "type": "failure",
                    "code": "M103",
                    "loc": error["loc"],
                    "summary": "Input should be a valid mapping",
                    "msg": (
                        f"Expected a mapping for field '{field}', but received a {input_type}.\n"
                        "If an empty mapping is intended, use '{}'."
                    ),
                    "input": error["input"],
                    "fix": "{}",
                }

            return {
                "type": "failure",
                "code": "M103",
                "loc": error["loc"],
                "summary": "Input should be a valid mapping",
                "msg": f"Expected a mapping for field '{field}', but received a {input_type}.",
                "input": error["input"],
            }

        case "decimal_parsing" | "decimal_type" | "float_parsing" | "float_type":
            field = _get_field(error["loc"])
            input_type = get_type_name(error["input"])
            return {
                "type": "failure",
                "code": "M103",
                "loc": error["loc"],
                "summary": "Input should be a valid number",
                "msg": f"Expected a number for field '{field}', but received a {input_type}.",
                "input": error["input"],
            }

        case "enum" | "literal_error":
            return translate_pydantic_enum_error(error)

        case "extra_forbidden":
            return translate_pydantic_extra_forbidden_error(error)

        case (
            "frozen_set_type"
            | "iterable_type"
            | "list_type"
            | "set_type"
            | "tuple_type"
        ):
            field = _get_field(error["loc"])
            input_type = get_type_name(error["input"])

            if not error["input"]:
                return {
                    "type": "failure",
                    "code": "M103",
                    "loc": error["loc"],
                    "summary": "Input should be a valid array",
                    "msg": (
                        f"Expected an array for field '{field}', but received a {input_type}.\n"
                        "If an empty array is intended, use '[]'."
                    ),
                    "input": error["input"],
                    "fix": "[]",
                }

            return {
                "type": "failure",
                "code": "M103",
                "loc": error["loc"],
                "summary": "Input should be a valid array",
                "msg": f"Expected an array for field '{field}', but received a {input_type}.",
                "input": error["input"],
            }

        case "int_parsing" | "int_type":
            field = _get_field(error["loc"])
            input_type = get_type_name(error["input"])
            return {
                "type": "failure",
                "code": "M103",
                "loc": error["loc"],
                "summary": "Input should be a valid integer",
                "msg": f"Expected a integer for field '{field}', but received a {input_type}.",
                "input": error["input"],
            }

        case "missing":
            field = _get_field(error["loc"])
            return {
                "type": "failure",
                "code": "M101",
                "loc": error["loc"],
                "summary": "Missing required field",
                "msg": f"Field '{field}' is required but missing",
            }

        case "string_type":
            return translate_pydantic_string_type_error(error)

        case "artifact_prohibited_value_field":
            diagnosis: Diagnosis = {
                "type": "failure",
                "code": "M102",
                "loc": error["loc"],
                "summary": "Invalid field for artifact",
                "msg": error["msg"],
                "input": Field("value"),
            }

            with contextlib.suppress(Exception):
                diagnosis["fix"] = json.dumps({"raw": {"data": error["input"]}})

            return diagnosis

        case "parameter_value_type_error":
            return translate_parameter_value_type_error(error)

    return {
        "type": "failure",
        "code": "M003",
        "loc": error["loc"],
        "msg": error["msg"],
        "input": error["input"],
        "ctx": {
            "pydantic_error": typing.cast("Bundle", error),
        },
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
        return "number"
    if isinstance(value, Mapping):
        return "mapping"
    if isinstance(value, Sequence):
        return "array"
    return type(value).__name__


def _get_field[T](loc: tuple[int | str, ...], default: T = "<unknown>") -> str | T:
    """
    Get the last string in the location tuple as the field name.

    Returns
    -------
    quoted : str
        The quoted field name for display.
    """
    for item in reversed(loc):
        if isinstance(item, str):
            return item
    return default


def translate_pydantic_enum_error(error: ErrorDetails) -> Diagnosis:
    """
    Translate a Pydantic `enum`_ error to a diagnosis object.

    .. _enum: https://docs.pydantic.dev/latest/errors/validation_errors/#enum
    """
    assert error["type"] in ("enum", "literal_error")

    expects_literal = error.get("ctx", {}).get("expected", "")
    expects_items = _extract_expects(expects_literal)

    field = _get_field(error["loc"])

    fix = None
    if result := extractOne(input_ := error["input"], expects_items):
        fix, _, _ = result

    return {
        "type": "failure",
        "code": "M104",
        "loc": error["loc"],
        "summary": error["msg"],
        "msg": (
            f"Input '{input_}' is not a valid value for field '{field}'.\n"
            f"Expected {expects_literal}."
        ),
        "input": input_,
        "fix": fix,
    }


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


def translate_pydantic_extra_forbidden_error(error: ErrorDetails) -> Diagnosis:
    """
    Translate a Pydantic `extra_forbidden`_ error to a diagnosis object.

    .. _extra_forbidden: https://docs.pydantic.dev/latest/errors/validation_errors/#extra_forbidden
    """
    assert error["type"] == "extra_forbidden"

    loc = error["loc"]
    field = _get_field(loc, default=None)
    assert field  # must present

    here = "here"
    if len(loc) > 1:
        parent = _get_field(loc[:-1])
        here = f"within '{parent}'"

    return {
        "type": "failure",
        "code": "M102",
        "loc": error["loc"],
        "summary": f"Unexpected field '{field}'",
        "msg": f"Field '{field}' is not allowed {here}. Remove it.",
        "input": Field(field),
    }


def translate_pydantic_string_type_error(error: ErrorDetails) -> Diagnosis:
    """
    Translate a Pydantic `string_type`_ error to a diagnosis object.

    This function constructs more helpful error message for string type validation
    errors, including suggestions based on the value and common YAML parsing pitfalls.

    .. _string_type: https://docs.pydantic.dev/latest/errors/validation_errors/#string_type

    See also
    --------
    `The yaml document from hell
       <https://ruudvanasseldonk.com/2023/01/11/the-yaml-document-from-hell>`_
    """
    assert error["type"] == "string_type"

    field = _get_field(error["loc"])
    input_value = error["input"]
    input_type = get_type_name(input_value)

    with io.StringIO() as buf:
        buf.write(
            f"Expected a string for field '{field}', but received a {input_type}.\n"
        )

        # the Norway problem
        if input_value is True:
            buf.write(
                "Unquoted values like 'True', 'Yes', 'On', 'Y' are parsed as booleans.\n"
            )
        elif input_value is False:
            buf.write(
                "Unquoted values like 'False', 'No', 'Off', 'N' are parsed as booleans.\n"
            )

        # sexagesimal
        if isinstance(input_value, int) and 60 < input_value <= 3600:
            sexagesimal = _to_sexagesimal(input_value)
            buf.write(
                f"Numbers separated by colons (e.g. {sexagesimal}) will be parsed as sexagesimal.\n"
            )

        # general suggestion
        buf.write("Quote string values to avoid parsing issues.")
        message = buf.getvalue()

    return {
        "type": "failure",
        "code": "M103",
        "loc": error["loc"],
        "summary": "Input should be a valid string",
        "msg": message,
        "input": error["input"],
    }


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


def translate_parameter_value_type_error(error: ErrorDetails) -> Diagnosis:
    """Customized translator for ``parameter_value_type_error``."""
    assert error["type"] == "parameter_value_type_error"

    with io.StringIO() as buf:
        input_type = get_type_name(error["input"])
        buf.write(f"Expected string for parameter value, but received a {input_type}.")

        if isinstance(error["input"], dict | list):
            buf.write("\n")
            buf.write(
                "If a complex structure is intended, serialize it as a JSON string."
            )

        message = buf.getvalue()

    diagnosis: Diagnosis = {
        "type": "failure",
        "code": "M103",
        "loc": error["loc"],
        "summary": "Input should be a string",
        "msg": message,
        "input": error["input"],
    }

    if isinstance(error["input"], dict | list):
        with contextlib.suppress(Exception):
            diagnosis["fix"] = json.dumps(error["input"], indent=2)

    return diagnosis
