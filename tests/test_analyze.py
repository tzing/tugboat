import json
import logging
import textwrap
from pathlib import Path

import pytest
import ruamel.yaml

from tests.dirty_equals import ContainsSubStrings
from tugboat.analyze import _find_related_comments, _should_ignore_code, analyze_yaml

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
