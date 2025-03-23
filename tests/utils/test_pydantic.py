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

from tugboat.schemas.basic import Array, Dict
from tugboat.utils.pydantic import (
    _compose_string_error_message,
    _extract_expects,
    _to_sexagesimal,
    bulk_translate_pydantic_errors,
    get_type_name,
    translate_pydantic_error,
)


class TestBulkTranslatePydanticError:

    def test(self):
        class Model(BaseModel):
            x: bool
            y: bool | int | float | str

        with pytest.raises(ValidationError) as exc_info:
            Model.model_validate({"x": None, "y": None})

        assert bulk_translate_pydantic_errors(exc_info.value.errors()) == [
            {
                "type": "failure",
                "code": "M103",
                "loc": ("x",),
                "summary": "Input should be a valid boolean",
                "msg": (
                    "Expected a boolean for field 'x', but received a null.\n"
                    "Try using 'true' or 'false' without quotes."
                ),
                "input": None,
            },
            {
                "type": "failure",
                "code": "M103",
                "loc": ("y",),
                "summary": "Input type mismatch",
                "msg": "Expected bool, float, int or str for field 'y', but received a null.",
                "input": None,
            },
        ]


class TestTranslatePydanticError:

    def test_bool_parsing(self):
        class Model(BaseModel):
            x: bool

        error = get_validation_error(Model, {"x": 1234})
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M103",
            "loc": ("x",),
            "summary": "Input should be a valid boolean",
            "msg": (
                "Expected a boolean for field 'x', but received a integer.\n"
                "Try using 'true' or 'false' without quotes."
            ),
            "input": 1234,
        }

    def test_dict_type_1(self):
        class Model(BaseModel):
            x: dict

        error = get_validation_error(Model, {"x": 1234})
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M103",
            "loc": ("x",),
            "summary": "Input should be a valid mapping",
            "msg": "Expected a mapping for field 'x', but received a integer.",
            "input": 1234,
        }

    def test_dict_type_2(self):
        class Model(BaseModel):
            x: Dict[str, int]

        error = get_validation_error(Model, {"x": None})
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M103",
            "loc": ("x",),
            "summary": "Input should be a valid mapping",
            "msg": (
                "Expected a mapping for field 'x', but received a null.\n"
                "If an empty mapping is intended, use '{}'."
            ),
            "input": None,
            "fix": "{}",
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
            "msg": (
                "Input 'hllo' is not a valid value for field 'x'.\n"
                "Expected 'hello' or 'world'."
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
            "code": "M102",
            "loc": ("x", 0, "z"),
            "summary": "Found redundant field",
            "msg": "Field 'z' is not valid within the 'x' section.",
            "input": "z",
        }

        # case 2 - extra field in the root model
        error = get_validation_error(Model, {"x": [{"y": "foo"}], "z": "bar"})
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M102",
            "loc": ("z",),
            "summary": "Found redundant field",
            "msg": "Field 'z' is not valid within current context.",
            "input": "z",
        }

    def test_float_parsing(self):
        class Model(BaseModel):
            x: float

        error = get_validation_error(Model, {"x": "foo"})
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M103",
            "loc": ("x",),
            "summary": "Input should be a valid floating point number",
            "msg": "Expected a floating point number for field 'x', but received a string.",
            "input": "foo",
        }

    def test_int_parsing(self):
        class Model(BaseModel):
            x: int

        error = get_validation_error(Model, {"x": "foo"})
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M103",
            "loc": ("x",),
            "summary": "Input should be a valid integer",
            "msg": "Expected a integer for field 'x', but received a string.",
            "input": "foo",
        }

    def test_list_error_1(self):
        class Model(BaseModel):
            x: list

        error = get_validation_error(Model, {"x": "foo"})
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M103",
            "loc": ("x",),
            "summary": "Input should be a valid array",
            "msg": "Expected an array for field 'x', but received a string.",
            "input": "foo",
        }

    def test_list_error_2(self):
        class Model(BaseModel):
            x: Array[int]

        error = get_validation_error(Model, {"x": {}})
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M103",
            "loc": ("x",),
            "summary": "Input should be a valid array",
            "msg": (
                "Expected an array for field 'x', but received a mapping.\n"
                "If an empty array is intended, use '[]'."
            ),
            "input": {},
            "fix": "[]",
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
            "msg": (
                "Input 'warudo' is not a valid value for field 'x'.\n"
                "Expected 'hello', 'world' or 'hola'."
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
            "code": "M101",
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
            "code": "M103",
            "loc": ("x",),
            "summary": "Input should be a valid string",
            "msg": (
                "Expected a string for field 'x', but received a null.\n"
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
            "code": "M103",
            "loc": (),
            "summary": "Input should be a valid integer",
            "msg": "Expected a integer for field <unnamed>, but received a string.",
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
            "Expected a string for field FOO, but received a boolean.",
            "Note that these inputs will be interpreted as boolean true: 'True', 'Yes', 'On', 'Y'.",
            "Try using quotes for strings to fix this issue.",
        ]
        assert list(_compose_string_error_message("FOO", False)) == [
            "Expected a string for field FOO, but received a boolean.",
            "Note that these inputs will be interpreted as boolean false: 'False', 'No', 'Off', 'N'.",
            "Try using quotes for strings to fix this issue.",
        ]

    def test_sexagesimal(self):
        assert list(_compose_string_error_message("FOO", 1342)) == [
            "Expected a string for field FOO, but received a integer.",
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
