import json
import logging
import textwrap
from pathlib import Path

import pytest
import ruamel.yaml
from pydantic import BaseModel

from tests.utils import ContainsSubStrings
from tugboat.analyze import (
    _find_related_comments,
    _get_line_column,
    _should_ignore_code,
    analyze_raw,
    analyze_yaml,
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

    def test_suppressed(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ):
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

        with caplog.at_level(logging.DEBUG):
            diagnoses = analyze_yaml(
                """
                apiVersion: v1
                kind: Test
                metadata:
                  generateName: test-
                spec:
                  foo: bar  # noqa: T01
                """
            )

        assert diagnoses == []
        assert (
            "Suppressed diagnosis T01 (Test diagnosis) in manifest test- at line 7, column 19"
            in caplog.text
        )

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


class TestGetRelatedComments:

    @pytest.fixture
    def document(self):
        yaml = ruamel.yaml.YAML()
        return yaml.load(
            textwrap.dedent(
                """
                spec:
                  # lorem ipsum dolor
                  # sit amet
                  name: sample # consectetur adipiscing

                  steps:
                    # tempor incididunt
                    - - name: baz # sed do
                        data: 123 # et dolore
                    - # ut enim ad minim
                      name: qux
                      var: {} # ullamco laboris nisi

                    - data: |- # ut aliquip ex ea
                        bla bla bla
                """
            )
        )

    @pytest.mark.parametrize(
        ("loc", "expected"),
        [
            (("spec", "name"), "consectetur adipiscing"),
            (("spec", "steps", 0, 0, "name"), "tempor incididunt"),
            (("spec", "steps", 0, 0, "name"), "sed do"),
            (("spec", "steps", 0, 0, "data"), "et dolore"),
            (("spec", "steps", 1), "tempor incididunt"),
            (("spec", "steps", 1, "var"), "ullamco laboris nisi"),
            (("spec", "steps", 2, "data"), "ut aliquip ex ea"),
        ],
    )
    def test_commented(self, document, loc, expected):
        comments = list(_find_related_comments(document, loc))
        logger.critical("related comments: %s", json.dumps(comments, indent=2))
        assert ContainsSubStrings(expected) in comments


class TestShouldIgnoreCode:

    def test_all(self):
        assert _should_ignore_code("T001", ["#NoQA; This is a comment"]) is True
        assert _should_ignore_code("T001", ["#noqa"]) is True

        assert _should_ignore_code("T001", ["#noqa: ALL"]) is False

    def test_specific(self):
        assert (
            _should_ignore_code("T001", ["#noqa: T001, T002; This is a comment"])
            is True
        )
        assert _should_ignore_code("T002", ["#noqa: t001, t002"]) is True

        assert (
            _should_ignore_code("T003", ["#noqa: T001; T003 is not for here"]) is False
        )


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
                # contains deprecated field
                "exit-handler-step-level.yaml",
                "template-on-exit.yaml",
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
