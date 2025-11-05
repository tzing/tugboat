import logging
import os
import re
import textwrap
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from tests.dirty_equals import IsPartialModel
from tugboat.engine import (
    DiagnosisModel,
    FilesystemMetadata,
    ManifestMetadata,
    analyze_yaml_document,
    analyze_yaml_stream,
    extract_helm_metadata,
    yaml_parser,
)

logger = logging.getLogger(__name__)


class TestDiagnosisModel:

    def test_minimal(self):
        diagnosis = DiagnosisModel.model_validate(
            {
                "code": "t01",
                "loc": (),
                "msg": "Test 1. Some extra message.",
            }
        )

        assert diagnosis.code == "T01"
        assert diagnosis.summary == "Test 1"
        assert diagnosis.loc_path == "."
        assert diagnosis.extras.file is None
        assert diagnosis.extras.helm is None
        assert diagnosis.extras.manifest is None

    def test_full(self):
        diagnosis = DiagnosisModel.model_validate(
            {
                "code": "T01",
                "loc": ("foo", 0, "bar"),
                "msg": "Test 2 with \nnew line.",
                "extras": {
                    "file": {
                        "filepath": "/path/to/file.yaml",
                    },
                    "helm": {
                        "chart": "my-chart",
                        "template": "templates/workflow.yaml",
                    },
                    "manifest": {
                        "group": "example.com",
                        "kind": "Test",
                        "name": "test-",
                    },
                },
            }
        )

        assert diagnosis.summary == "Test 2 with"
        assert diagnosis.loc_path == ".foo[0].bar"

        assert diagnosis.extras.file
        assert diagnosis.extras.file.filepath == "/path/to/file.yaml"
        assert not diagnosis.extras.file.is_stdin

        assert diagnosis.extras.helm
        assert diagnosis.extras.helm.chart == "my-chart"
        assert diagnosis.extras.helm.template == "templates/workflow.yaml"

        assert diagnosis.extras.manifest
        assert diagnosis.extras.manifest.fqk == "test.example.com"
        assert diagnosis.extras.manifest.fqkn == "test.example.com/test-"

    class TestFilesystemMetadata:

        def test_stdin_1(self):
            metadata = FilesystemMetadata.model_validate({"filepath": "<stdin>"})
            assert metadata.is_stdin

        @pytest.mark.skipif(
            os.name != "posix", reason="Only relevant on Unix-like systems"
        )
        def test_stdin_2(self, tmp_path: Path):
            filepath = tmp_path / "manifest.yaml"
            filepath.symlink_to("/dev/stdin")

            metadata = FilesystemMetadata.model_validate({"filepath": str(filepath)})
            assert metadata.is_stdin

    class TestManifestMetadata:

        def test_core_api_group(self):
            metadata = ManifestMetadata.model_validate(
                {
                    "group": "",
                    "kind": "Pod",
                    "name": "my-pod",
                }
            )

            assert metadata.fqk == "pod"
            assert metadata.fqkn == "pod/my-pod"

        def test_missing_name(self):
            metadata = ManifestMetadata.model_validate(
                {
                    "group": "example.com",
                    "kind": "Test",
                }
            )

            assert metadata.fqk == "test.example.com"

            with pytest.raises(ValueError, match=re.escape("name is not set")):
                _ = metadata.fqkn


class TestAnalyzeYamlStream:

    def test(self):
        diagnoses = analyze_yaml_stream(
            textwrap.dedent(
                """
                # Source: my-chart/templates/debug.yaml
                apiVersion: tugboat.example.com/v1
                kind: Debug
                metadata:
                  generateName: test-
                spec:
                  foo: bar
                """
            ),
            "/path/to/file.yaml",
        )
        assert diagnoses == [
            DiagnosisModel.model_validate(
                {
                    "line": 8,
                    "column": 3,
                    "type": "failure",
                    "code": "M102",
                    "loc": ("spec", "foo"),
                    "summary": "Found redundant field",
                    "msg": "Field 'foo' is not valid within the 'spec' section.",
                    "input": "foo",
                    "extras": {
                        "file": {
                            "filepath": "/path/to/file.yaml",
                        },
                        "helm": {
                            "chart": "my-chart",
                            "template": "templates/debug.yaml",
                        },
                        "manifest": {
                            "group": "tugboat.example.com",
                            "kind": "Debug",
                            "name": "test-",
                        },
                    },
                }
            )
        ]

    def test_empty_yaml(self):
        diagnoses = analyze_yaml_stream(
            textwrap.dedent(
                """
                ---
                apiVersion: tugboat.example.com/v1
                kind: Debug
                metadata:
                  generateName: test-

                ---
                # This is an empty document
                """
            )
        )
        assert diagnoses == []

    def test_not_a_manifest(self):
        diagnoses = analyze_yaml_stream(
            textwrap.dedent(
                """
                foo: bar
                """
            )
        )
        assert diagnoses == [IsPartialModel(code="M001")]

    def test_yaml_error(self):
        diagnoses = analyze_yaml_stream('test: "foo')
        assert diagnoses == [
            IsPartialModel(
                line=1,
                column=11,
                type="error",
                code="F002",
                loc=(),
                summary="Malformed YAML document",
                extras={
                    "file": None,
                    "helm": None,
                    "manifest": None,
                },
            )
        ]

    def test_malformed_document_structure(self):
        diagnoses = analyze_yaml_stream(
            textwrap.dedent(
                """
                - foo
                - bar
                """
            )
        )
        assert diagnoses == [
            IsPartialModel(
                line=2,
                column=1,
                type="error",
                code="F003",
                loc=(),
                summary="Malformed document structure",
            )
        ]

    def test_type_error(self):
        diagnoses = analyze_yaml_stream("this is a plain text document")
        assert diagnoses == [
            IsPartialModel(
                line=1,
                column=1,
                type="error",
                code="F002",
                loc=(),
                summary="Malformed input",
            )
        ]

    def test_with_argo_examples(self, argo_example_dir: Path):
        """
        This test is an integration test that make sure that our rules are valid
        for (almost) all examples from Argo Workflows official repository.
        """
        workflow_binding_dir = argo_example_dir / "workflow-event-binding"
        EXCLUDES = {
            # invalid reference
            workflow_binding_dir / "event-consumer-workflowtemplate.yaml",
            # param value is an object, expected a string
            workflow_binding_dir / "github-path-filter-workflowtemplate.yaml",
        }

        ta = TypeAdapter(list[DiagnosisModel])

        for file_path in argo_example_dir.glob("**/*.yaml"):
            # skip known false positives
            if file_path in EXCLUDES:
                continue

            logger.debug("Checking %s", file_path)

            # analyze
            diagnoses = analyze_yaml_stream(file_path.read_text())

            # skip warnings
            diagnoses = list(filter(lambda d: d.type != "warning", diagnoses))

            # fail on errors
            if any(diagnoses):
                logger.critical(
                    "diagnoses: %s",
                    ta.dump_json(
                        diagnoses,
                        indent=2,
                        exclude_none=True,
                        exclude_unset=True,
                    ).decode(),
                )
                pytest.fail(f"Found issue with {file_path}")


class TestAnalyzeYamlDocument:

    def test(self, monkeypatch: pytest.MonkeyPatch):
        # this is a mocked test case
        monkeypatch.setattr(
            "tugboat.engine.analyze_manifest",
            lambda _: [
                {
                    "code": "T01",
                    "loc": ["spec", "foo"],
                    "summary": "Test diagnosis",
                    "msg": "This is a test diagnosis.",
                    "ctx": {
                        "manifest": {
                            "group": "example.com",
                            "kind": "Mock",
                            "name": "test-",
                        }
                    },
                }
            ],
        )

        diagnoses = analyze_yaml_document(
            yaml_parser.load(
                textwrap.dedent(
                    """
                    apiVersion: v1
                    kind: Test
                    metadata:
                      generateName: test-
                    spec:
                      foo: bar
                    """
                )
            )
        )

        assert list(diagnoses) == [
            IsPartialModel(
                line=7,
                column=8,
                type="failure",
                code="T01",
                loc=("spec", "foo"),
                summary="Test diagnosis",
                msg="This is a test diagnosis.",
            )
        ]

    def test_suppression(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ):
        monkeypatch.setattr(
            "tugboat.engine.analyze_manifest",
            lambda _: [
                {
                    "code": "T01",
                    "loc": ("spec", "foo"),
                    "msg": "",
                    "ctx": {
                        "manifest": {
                            "group": "example.com",
                            "kind": "Mock",
                            "name": "test-",
                        }
                    },
                }
            ],
        )

        with caplog.at_level("DEBUG"):
            diagnoses = analyze_yaml_document(
                yaml_parser.load(
                    textwrap.dedent(
                        """
                        apiVersion: v1
                        kind: Test
                        metadata:
                          generateName: test-
                        spec:
                          foo: bar  # noqa: T01
                        """
                    )
                )
            )
            assert list(diagnoses) == []

        assert (
            "Diagnosis T01 (<no summary>) at test-:.spec.foo is suppressed by comment"
            in caplog.text
        )


class TestExtractHelmMetadata:

    def test_success(self):
        doc = yaml_parser.load(
            textwrap.dedent(
                """
                # Source: my-chart/templates/pod.yaml
                apiVersion: v1
                kind: Pod
                """
            )
        )

        metadata = extract_helm_metadata(doc)
        assert metadata == {
            "chart": "my-chart",
            "template": "templates/pod.yaml",
        }

    def test_missing_comment_1(self):
        doc = yaml_parser.load(
            textwrap.dedent(
                """
                apiVersion: v1
                kind: Pod
                """
            )
        )
        assert extract_helm_metadata(doc) is None

    def test_missing_comment_2(self):
        doc = yaml_parser.load(
            textwrap.dedent(
                """
                [] # Source: my-chart/templates/pod.yaml (not at the top)
                """
            )
        )
        assert extract_helm_metadata(doc) is None

    def test_unrelated_comment_1(self):
        doc = yaml_parser.load(
            textwrap.dedent(
                """
                  # Source: my-chart/templates/pod.yaml (slightly indented)
                apiVersion: v1
                kind: Pod
                """
            )
        )
        assert extract_helm_metadata(doc) is None

    def test_unrelated_comment_2(self):
        doc = yaml_parser.load(
            textwrap.dedent(
                """
                # Hello world!
                apiVersion: v1
                kind: Pod
                """
            )
        )
        assert extract_helm_metadata(doc) is None
