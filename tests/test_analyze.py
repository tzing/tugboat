import enum
import json
import logging
import textwrap
from pathlib import Path
from typing import Literal

import pytest
import ruamel.yaml
from dirty_equals import IsPartialDict
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from pydantic_core import ErrorDetails

from tests.utils import ContainsSubStrings
from tugboat.analyze import (
    _extract_expects,
    _get_line_column,
    _guess_string_problems,
    _to_sexagesimal,
    analyze_raw,
    analyze_yaml,
    get_type_name,
    translate_pydantic_error,
)
from tugboat.core import hookimpl
from tugboat.schemas import Manifest

logger = logging.getLogger(__name__)


class TestAnalyzeYaml:
    def test_standard(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            "tugboat.analyze.analyze_raw",
            lambda _: [
                {
                    "code": "T01",
                    "loc": ("spec", "foo"),
                    "msg": "Test diagnosis. This is a long message.",
                }
            ],
        )

        diagnoses = analyze_yaml(
            """
            apiVersion: v1
            kind: Test
            metadata:
              generateName: test-
            spec:
              foo: bar
            """
        )
        assert diagnoses == [
            {
                "line": 7,
                "column": 15,
                "type": "failure",
                "code": "T01",
                "manifest": "test-",
                "loc": ("spec", "foo"),
                "summary": "Test diagnosis",
                "msg": "Test diagnosis. This is a long message.",
                "input": None,
                "fix": None,
            }
        ]

    def test_plain_text(self):
        diagnoses = analyze_yaml(
            """
            This is a plain text document.
            """
        )
        assert diagnoses == [
            {
                "line": 1,
                "column": 1,
                "type": "error",
                "code": "F002",
                "manifest": None,
                "loc": (),
                "summary": "Malformed YAML document",
                "msg": "The input is not a YAML document",
                "input": None,
                "fix": None,
            }
        ]

    def test_yaml_error(self):
        diagnoses = analyze_yaml(
            """
            test: "foo
            """
        )
        assert diagnoses == [
            {
                "line": 3,
                "column": 13,
                "type": "error",
                "code": "F002",
                "manifest": None,
                "loc": (),
                "summary": "Malformed YAML document",
                "msg": ContainsSubStrings("found unexpected end of stream"),
                "input": None,
                "fix": None,
            }
        ]

    def test_yaml_input_error(self):
        diagnoses = analyze_yaml(
            """
            - foo
            - bar
            """
        )
        assert diagnoses == [
            {
                "line": 2,
                "column": 13,
                "type": "error",
                "code": "F003",
                "manifest": None,
                "loc": (),
                "summary": "Malformed document structure",
                "msg": "The YAML document should be a mapping",
                "input": None,
                "fix": None,
            }
        ]


class TestGetLineColumn:
    @pytest.fixture
    def document(self):
        yaml = ruamel.yaml.YAML()
        return yaml.load(
            textwrap.dedent(
                """
                spec:
                  name: sample

                  steps:
                    - - name: baz
                        data: 123
                    - name: qux
                      var: {}
                """
            )
        )

    @pytest.mark.parametrize(
        ("loc", "expected"),
        [
            (("spec",), (1, 0)),
            (("spec", "name"), (2, 2)),
            (("spec", "steps"), (4, 2)),
            (("spec", "steps", 0, 0, "data"), (6, 8)),
            (("spec", "foo"), (1, 0)),
            (("spec", "steps", 1, "var", "foo"), (8, 6)),
        ],
    )
    def test(self, document, loc, expected):
        assert _get_line_column(document, loc) == expected


class TestAnalyzeRaw:
    @hookimpl(tryfirst=True)
    def parse_manifest(self, manifest: dict):
        if manifest.get("kind") == "Unrecognized":
            return
        if manifest.get("kind") == "NotManifest":
            return "Not a manifest object"
        if manifest.get("kind") == "ParseError":
            raise RuntimeError("Test exception")

        class Spec(BaseModel):
            foo: str

        class MockManifest(Manifest[Spec]): ...

        return MockManifest.model_validate(manifest)

    @hookimpl(tryfirst=True)
    def analyze(self, manifest):
        if manifest.kind == "AnalysisError":
            raise RuntimeError("Test exception")

        yield {"code": "T01", "loc": (), "msg": "Test 1"}
        yield {"code": "T04", "loc": ("spec", "foo"), "msg": "Test 2"}
        yield {"code": "T02", "loc": ("spec", "foo"), "msg": "Test 3"}
        yield {
            "code": "T03",
            "loc": ("spec"),
            "msg": """
                Test 4. This is a long message that should be wrapped across
                multiple lines to test the formatting.
                """,
        }

    def test_standard(self, plugin_manager):
        plugin_manager.register(self)

        diagnoses = analyze_raw(
            {
                "apiVersion": "v1",
                "kind": "Test",
                "metadata": {"name": "test"},
                "spec": {"foo": "bar"},
            }
        )
        assert diagnoses == [
            {
                "code": "T01",
                "loc": (),
                "msg": "Test 1",
            },
            {
                "code": "T03",
                "loc": ("spec"),
                "msg": "Test 4. This is a long message that should be wrapped across\n"
                "multiple lines to test the formatting.",
            },
            {
                "code": "T02",
                "loc": ("spec", "foo"),
                "msg": "Test 3",
            },
            {
                "code": "T04",
                "loc": ("spec", "foo"),
                "msg": "Test 2",
            },
        ]

    def test_not_kubernetes_manifest(self, plugin_manager):
        plugin_manager.register(self)

        diagnoses = analyze_raw({"foo": "bar"})
        assert diagnoses == [
            {
                "type": "skipped",
                "code": "M001",
                "loc": (),
                "summary": "Not a Kubernetes manifest",
                "msg": "The input does not look like a Kubernetes manifest",
            }
        ]

    def test_parse_manifest_validation_error(self, plugin_manager):
        plugin_manager.register(self)

        diagnoses = analyze_raw(
            {
                "apiVersion": "v1",
                "kind": "Test",
                "metadata": {"name": "test"},
            }
        )
        assert diagnoses == [
            {
                "type": "failure",
                "code": "M004",
                "loc": ("spec",),
                "summary": "Missing required field",
                "msg": "Field 'spec' is required but missing",
            }
        ]

    def test_parse_manifest_exception(self, plugin_manager):
        plugin_manager.register(self)

        diagnoses = analyze_raw(
            {
                "apiVersion": "v1",
                "kind": "ParseError",
            }
        )
        assert diagnoses == [
            {
                "type": "error",
                "code": "F001",
                "loc": (),
                "summary": "Internal error while analyzing manifest",
                "msg": "An error occurred while parsing the manifest: Test exception",
            }
        ]

    def test_unrecognized_kind(self, plugin_manager):
        plugin_manager.register(self)

        diagnoses = analyze_raw(
            {
                "apiVersion": "v1",
                "kind": "Unrecognized",
            }
        )
        assert diagnoses == []

    def test_not_manifest_obj(self, plugin_manager):
        plugin_manager.register(self)

        diagnoses = analyze_raw(
            {
                "apiVersion": "v1",
                "kind": "NotManifest",
            }
        )
        assert diagnoses == [
            {
                "type": "error",
                "code": "F001",
                "loc": (),
                "summary": "Internal error while analyzing manifest",
                "msg": "Expected a Manifest object, got <class 'str'>",
            }
        ]

    def test_analyze_error(self, plugin_manager):
        plugin_manager.register(self)

        diagnoses = analyze_raw(
            {
                "apiVersion": "v1",
                "kind": "AnalysisError",
                "metadata": {"generateName": "test-"},
                "spec": {"foo": "bar"},
            }
        )
        assert diagnoses == [
            {
                "type": "error",
                "code": "F001",
                "loc": (),
                "summary": "Internal error while analyzing manifest",
                "msg": "An error occurred while analyzing the manifest: Test exception",
            }
        ]


class TestArgoExamples:
    """
    Make sure our schemas are valid for (almost) all examples from Argo.
    """

    def test(self, argo_example_dir: Path):
        for file_path in argo_example_dir.glob("**/*.yaml"):
            # skip known false positives
            if file_path.name in (
                # invalid schema
                "exit-handler-step-level.yaml",
                "template-on-exit.yaml",
                "webhdfs-input-output-artifacts.yaml",
                # invalid reference
                "event-consumer-workflowtemplate.yaml",
                # name too long
                "global-parameters-from-configmap-referenced-as-local-variable.yaml",
            ):
                continue

            # analyze
            diagnoses = analyze_yaml(file_path.read_text())

            # skip warnings
            diagnoses = list(filter(lambda d: d["type"] != "skipped", diagnoses))

            # fail on errors
            if any(diagnoses):
                logger.critical("diagnoses: %s", json.dumps(diagnoses, indent=2))
                pytest.fail(f"Found issue with {file_path}")


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
        assert _to_sexagesimal(1) == "1"
        assert _to_sexagesimal(1342) == "22:22"
        assert _to_sexagesimal(-4321) == "-1:12:1"


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


def _get_error(model: type[BaseModel], input: dict) -> ErrorDetails:
    try:
        model.model_validate(input)
    except ValidationError as exc:
        return exc.errors()[0]
    raise RuntimeError("No error raised")
