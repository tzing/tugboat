import json
import logging
from pathlib import Path

import pytest

from tests.dirty_equals import ContainsSubStrings
from tugboat.analyze import analyze_yaml

logger = logging.getLogger(__name__)


class TestAnalyzeYaml:
    def test_standard(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            "tugboat.analyze.analyze_manifest",
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
                "column": 20,
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
            "tugboat.analyze.analyze_manifest",
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
            "Suppressed diagnosis T01 (Test diagnosis) in manifest test- at line 7, column 24"
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


class TestArgoExamples:
    """
    Make sure our schemas are valid for (almost) all examples from Argo.
    """

    def test(self, argo_example_dir: Path):
        workflow_binding_dir = argo_example_dir / "workflow-event-binding"

        EXCLUDES = {
            # invalid reference
            workflow_binding_dir / "event-consumer-workflowtemplate.yaml",
            # param value is an object, expected a string
            workflow_binding_dir / "github-path-filter-workflowtemplate.yaml",
        }

        for file_path in argo_example_dir.glob("**/*.yaml"):
            # skip known false positives
            if file_path in EXCLUDES:
                continue

            # analyze
            diagnoses = analyze_yaml(file_path.read_text())

            # skip warnings
            diagnoses = list(filter(lambda d: d["type"] != "warning", diagnoses))

            # fail on errors
            if any(diagnoses):
                logger.critical("diagnoses: %s", json.dumps(diagnoses, indent=2))
                pytest.fail(f"Found issue with {file_path}")
