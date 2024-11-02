import enum
from typing import Any, Literal

from dirty_equals import DirtyEquals, IsPartialDict
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from pydantic_core import ErrorDetails

from tugboat.analyzers.pydantic import (
    _extract_expects,
    _guess_string_problems,
    to_sexagesimal,
    translate_pydantic_error,
)


class TestTranslatePydanticError:
    def test_bool_type(self):
        class Model(BaseModel):
            x: bool

        error = _get_error(Model, {"x": 1234})
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

        error = _get_error(Model, {"x": "hllo"})
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
        error = _get_error(Model, {"x": [{"y": "foo", "z": "bar"}]})
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M005",
            "loc": ("x", 0, "z"),
            "summary": "Found redundant field",
            "msg": "Field 'z' is not valid within the 'x' section.",
            "input": "z",
        }

        # case 2 - extra field in the root model
        error = _get_error(Model, {"x": [{"y": "foo"}], "z": "bar"})
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

        error = _get_error(Model, {"x": "foo"})
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

        error = _get_error(Model, {"x": "warudo"})
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

        error = _get_error(Model, {})
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

        error = _get_error(Model, {"x": None})
        assert translate_pydantic_error(error) == {
            "type": "failure",
            "code": "M007",
            "loc": ("x",),
            "summary": "Input should be a valid string",
            "msg": (
                "Field 'x' should be a valid string, got NoneType.\n"
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

        error = _get_error(Model, {"x": "foo"})
        assert translate_pydantic_error(error) == IsPartialDict(
            {
                "type": "failure",
                "code": "M003",
                "loc": ("x",),
                "msg": "Value error, test error",
                "input": "foo",
            }
        )


class TestExtractExpects:
    def test_enum(self):
        class MyEnum(enum.StrEnum):
            hello = "hello"
            world = "world"

        class Model(BaseModel):
            x: MyEnum

        error = _get_error(Model, {"x": ""})
        expects = _extract_expects(error["ctx"]["expected"])
        assert list(expects) == ["hello", "world"]

    def test_literal(self):
        class Model(BaseModel):
            x: Literal["hello", "world", "hola'"]

        error = _get_error(Model, {"x": ""})
        expects = _extract_expects(error["ctx"]["expected"])
        assert list(expects) == ["hello", "world", "hola'"]

    def test_empty(self):
        assert list(_extract_expects("")) == []


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
            "Sequence of number separated by colons (e.g. 22:22) will be interpreted as sexagesimal.",
            "Try using quotes for strings to fix this issue.",
        ]


class TestToSexagesimal:
    def test(self):
        assert to_sexagesimal(1) == "1"
        assert to_sexagesimal(1342) == "22:22"
        assert to_sexagesimal(-4321) == "-1:12:1"


def _get_error(model: type[BaseModel], input: dict) -> ErrorDetails:
    try:
        model.model_validate(input)
    except ValidationError as exc:
        return exc.errors()[0]
    raise RuntimeError("No error raised")


class ContainsSubStrings(DirtyEquals[str]):
    def __init__(self, *text: str):
        self.texts = text

    def equals(self, other: Any) -> bool:
        return all(text in other for text in self.texts)
