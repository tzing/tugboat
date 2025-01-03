import enum
from typing import Any, Literal

import pytest
from dirty_equals import IsPartialDict
from pydantic import TypeAdapter, ValidationError
from pydantic_core import ErrorDetails

from tugboat.analyzers.pydantic import (
    _extract_expects,
    _guess_string_problems,
    _to_sexagesimal,
    get_type_name,
)


class TestExtractExpects:
    def test_enum(self):
        class MyEnum(enum.StrEnum):
            hello = "hello"
            world = "world"

        error = get_validation_error(MyEnum, {"x": ""})
        expects = _extract_expects(error["ctx"]["expected"])  # type: ignore
        assert list(expects) == ["hello", "world"]

    def test_literal(self):
        error = get_validation_error(Literal["hello", "world", "hola'"], "")  # type: ignore
        expects = _extract_expects(error["ctx"]["expected"])  # type: ignore
        assert list(expects) == ["hello", "world", "hola'"]

    def test_empty(self):
        assert list(_extract_expects("")) == []


class TestGetTypeName:
    @pytest.mark.parametrize(
        ("input_", "expected"),
        [
            (1234, "integer"),
            (3.14, "floating point number"),
            ("foo", "string"),
            (True, "boolean"),
            ({"x": 1}, "mapping"),
            ([1, 2, 3], "sequence"),
            ((1, 2, 3), "sequence"),
            (None, "null"),
            (IsPartialDict({}), "IsPartialDict"),
        ],
    )
    def test(self, input_, expected):
        assert get_type_name(input_) == expected


class TestGuessStringProblems:

    def test_norway_problem(self):
        assert list(_guess_string_problems(True)) == [
            "Note that these inputs will be interpreted as boolean true: 'True', 'Yes', 'On', 'Y'.",
            "Try using quotes for strings to fix this issue.",
        ]
        assert list(_guess_string_problems(False)) == [
            "Note that these inputs will be interpreted as boolean false: 'False', 'No', 'Off', 'N'.",
            "Try using quotes for strings to fix this issue.",
        ]

    def test_sexagesimal(self):
        assert list(_guess_string_problems(1342)) == [
            "Numbers separated by colons (e.g. 22:22) will be interpreted as sexagesimal.",
            "Try using quotes for strings to fix this issue.",
        ]


class TestToSexagesimal:

    def test(self):
        assert _to_sexagesimal(1) == "1"
        assert _to_sexagesimal(1342) == "22:22"
        assert _to_sexagesimal(-4321) == "-1:12:1"


def get_validation_error(type_: type, input_: Any) -> ErrorDetails:
    with pytest.raises(ValidationError) as exc_info:
        TypeAdapter(type_).validate_python(input_)
    return exc_info.value.errors()[0]
