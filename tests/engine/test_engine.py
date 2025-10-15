import json
import logging
import os
import re
import textwrap
from pathlib import Path

import pytest

from tests.dirty_equals import IsPartialModel
from tugboat.engine import (
    DiagnosisModel,
    FilesystemMetadata,
    ManifestMetadata,
    analyze_yaml_stream,
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
                    "line": 7,
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
                        "manifest": {
                            "group": "tugboat.example.com",
                            "kind": "Debug",
                            "name": "test-",
                        },
                    },
                }
            )
        ]

    class TestAnalyzeYamlDocument:
        # NOTE: use `analyze_yaml_stream` so i don't need to parse YAML manually

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

            diagnoses = analyze_yaml_stream(
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

            assert diagnoses == [
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
                diagnoses = analyze_yaml_stream(
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

            assert diagnoses == []
            assert (
                "Diagnosis T01 (<no summary>) at test-:.spec.foo is suppressed by comment"
                in caplog.text
            )

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
                logger.critical("diagnoses: %s", json.dumps(diagnoses, indent=2))
                pytest.fail(f"Found issue with {file_path}")
