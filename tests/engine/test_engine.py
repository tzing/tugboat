import textwrap

import pytest
from dirty_equals import IsPartialDict

from tests.dirty_equals import ContainsSubStrings
from tugboat.engine import analyze_yaml_stream


def test_analyze_yaml_stream_1(monkeypatch: pytest.MonkeyPatch):
    # this is a mocked test case
    monkeypatch.setattr(
        "tugboat.engine.analyze_manifest",
        lambda _: [
            {
                "code": "T01",
                "loc": ("spec", "foo"),
                "summary": "Test diagnosis",
                "msg": "This is a test diagnosis.",
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
        {
            "line": 7,
            "column": 8,
            "type": "failure",
            "code": "T01",
            "manifest": "test-",
            "loc": ("spec", "foo"),
            "summary": "Test diagnosis",
            "msg": "This is a test diagnosis.",
            "input": None,
            "fix": None,
        }
    ]


def tets_analyze_yaml_stream_2():
    # this is an integration test case
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
        )
    )
    assert diagnoses == [
        {
            "manifest": "test-",
            "line": 7,
            "column": 8,
            "type": "failure",
            "code": "M102",
            "loc": ("spec", "foo"),
            "summary": "Found redundant field",
            "msg": "Field 'foo' is not valid within the 'spec' section.",
            "input": "foo",
            "fix": None,
        }
    ]


def test_yaml_error():
    diagnoses = analyze_yaml_stream('test: "foo', "<test>")
    assert diagnoses == [
        {
            "line": 1,
            "column": 11,
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


def test_empty_yaml():
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


def test_malformed_document_structure():
    diagnoses = analyze_yaml_stream(
        textwrap.dedent(
            """
            - foo
            - bar
            """
        )
    )
    assert diagnoses == [
        IsPartialDict(
            {
                "line": 2,
                "column": 1,
                "type": "error",
                "code": "F003",
                "loc": (),
                "summary": "Malformed document structure",
            }
        )
    ]


def test_type_error():
    diagnoses = analyze_yaml_stream("this is a plain text document")
    assert diagnoses == [
        IsPartialDict(
            {
                "line": 1,
                "column": 1,
                "type": "error",
                "code": "F002",
                "manifest": None,
                "loc": (),
                "summary": "Malformed input",
                "input": None,
                "fix": None,
            }
        )
    ]


def test_suppression(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    monkeypatch.setattr(
        "tugboat.engine.analyze_manifest",
        lambda _: [
            {
                "code": "T01",
                "loc": ("spec", "foo"),
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
        "Diagnosis T01 (<no summary>) at test-:spec.foo is suppressed by comment"
        in caplog.text
    )
