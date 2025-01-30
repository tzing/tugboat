import enum
from typing import Any, Literal

import pytest
from dirty_equals import IsPartialDict
from pydantic import (
    BaseModel,
    ConfigDict,
    TypeAdapter,
    ValidationError,
    field_validator,
)
from pydantic_core import ErrorDetails

from tests.dirty_equals import ContainsSubStrings
from tugboat.utils.pydantic import (
    _compose_string_error_message,
    _extract_expects,
    _to_sexagesimal,
    get_type_name,
    translate_pydantic_error,
)


class TestTranslatePydanticError:

    def test_bool_type(self):
        class Model(BaseModel):
            x: bool

        error = get_validation_error(Model, {"x": 1234})
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M007",
            "loc": ("x",),
            "summary": "Input should be a valid boolean",
            "msg": ContainsSubStrings(
                "Field 'x' should be a valid boolean, got integer."
            ),
            "input": 1234,
        }

    def test_enum(self):
        class MyEnum(enum.StrEnum):
            hello = "hello"
            world = "world"

        class Model(BaseModel):
            x: MyEnum

        error = get_validation_error(Model, {"x": "hllo"})
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M008",
            "loc": ("x",),
            "summary": "Input should be 'hello' or 'world'",
            "msg": ContainsSubStrings(
                "Input 'hllo' is not a valid value for field 'x'.",
                "Expected 'hello' or 'world'.",
            ),
            "input": "hllo",
            "fix": "hello",
        }

    def test_extra_forbidden(self):
        class SubModel(BaseModel):
            model_config = ConfigDict(extra="forbid")
            y: str

        class Model(BaseModel):
            model_config = ConfigDict(extra="forbid")
            x: list[SubModel]

        # case 1 - extra field in the submodel
        error = get_validation_error(Model, {"x": [{"y": "foo", "z": "bar"}]})
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M005",
            "loc": ("x", 0, "z"),
            "summary": "Found redundant field",
            "msg": "Field 'z' is not valid within the 'x' section.",
            "input": "z",
        }

        # case 2 - extra field in the root model
        error = get_validation_error(Model, {"x": [{"y": "foo"}], "z": "bar"})
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M005",
            "loc": ("z",),
            "summary": "Found redundant field",
            "msg": "Field 'z' is not valid within current context.",
            "input": "z",
        }

    def test_int_type(self):
        class Model(BaseModel):
            x: int

        error = get_validation_error(Model, {"x": "foo"})
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M007",
            "loc": ("x",),
            "summary": "Input should be a valid integer",
            "msg": "Field 'x' should be a valid integer, got string.",
            "input": "foo",
        }

    def test_literal_error(self):
        class Model(BaseModel):
            x: Literal["hello", "world", "hola"]

        error = get_validation_error(Model, {"x": "warudo"})
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M008",
            "loc": ("x",),
            "summary": "Input should be 'hello', 'world' or 'hola'",
            "msg": ContainsSubStrings(
                "Input 'warudo' is not a valid value for field 'x'.",
                "Expected 'hello', 'world' or 'hola'.",
            ),
            "input": "warudo",
            "fix": "world",
        }

    def test_missing(self):
        class Model(BaseModel):
            x: str

        error = get_validation_error(Model, {})
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M004",
            "loc": ("x",),
            "summary": "Missing required field",
            "msg": "Field 'x' is required but missing",
        }

    def test_string_type(self):
        class Model(BaseModel):
            x: str

        error = get_validation_error(Model, {"x": None})
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M007",
            "loc": ("x",),
            "summary": "Input should be a valid string",
            "msg": (
                "Field 'x' should be a valid string, got null.\n"
                "Try using quotes for strings to fix this issue."
            ),
            "input": None,
        }

    def test_general_error(self):
        class Model(BaseModel):
            x: str

            @field_validator("x")
            @classmethod
            def _validate(cls, v):
                raise ValueError("test error")

        error = get_validation_error(Model, {"x": "foo"})
        assert translate_pydantic_error(error) == IsPartialDict(
            {
                "type": "failure",
                "code": "M003",
                "loc": ("x",),
                "msg": "Value error, test error",
                "input": "foo",
            }
        )

    def test_type_adapter(self):
        error = get_validation_error(int, "foo")
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M007",
            "loc": (),
            "summary": "Input should be a valid integer",
            "msg": "Field <unnamed> should be a valid integer, got string.",
            "input": "foo",
        }


class TestExtractExpects:
    def test_enum(self):
        class MyEnum(enum.StrEnum):
            hello = "hello"
            world = "world"

        error = get_validation_error(MyEnum, {"x": ""})
        expects = _extract_expects(error["ctx"]["expected"])
        assert list(expects) == ["hello", "world"]

    def test_literal(self):
        error = get_validation_error(Literal["hello", "world", "hola'"], "")
        expects = _extract_expects(error["ctx"]["expected"])
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
            ([1, 2, 3], "array"),
            ((1, 2, 3), "array"),
            (None, "null"),
            (IsPartialDict({}), "IsPartialDict"),
        ],
    )
    def test(self, input_, expected):
        assert get_type_name(input_) == expected


class TestComposeStringErrorMessage:

    def test_norway_problem(self):
        assert list(_compose_string_error_message("FOO", True)) == [
            "Field FOO should be a valid string, got boolean.",
            "Note that these inputs will be interpreted as boolean true: 'True', 'Yes', 'On', 'Y'.",
            "Try using quotes for strings to fix this issue.",
        ]
        assert list(_compose_string_error_message("FOO", False)) == [
            "Field FOO should be a valid string, got boolean.",
            "Note that these inputs will be interpreted as boolean false: 'False', 'No', 'Off', 'N'.",
            "Try using quotes for strings to fix this issue.",
        ]

    def test_sexagesimal(self):
        assert list(_compose_string_error_message("FOO", 1342)) == [
            "Field FOO should be a valid string, got integer.",
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
