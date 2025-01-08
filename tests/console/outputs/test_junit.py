import io
import re
from pathlib import Path

from tugboat.console.outputs.junit import JUnitOutputBuilder


class TestJUnitOutputBuilder:

    def test_1(self):
        builder = JUnitOutputBuilder()
        builder.update(
            path=Path("sample-workflow.yaml"),
            content="",
            diagnoses=[
                {
                    "type": "error",
                    "line": 1,
                    "column": 1,
                    "code": "T01",
                    "manifest": "hello-world-",
                    "loc": (),
                    "summary": "Test error",
                    "msg": "Test error message",
                    "input": None,
                    "fix": None,
                },
                {
                    "type": "skipped",
                    "line": 2,
                    "column": 1,
                    "code": "T03",
                    "manifest": "hello-world-",
                    "loc": ("kind",),
                    "summary": "Test skipped",
                    "msg": "Test skipped message",
                    "input": None,
                    "fix": None,
                },
            ],
        )

        with io.StringIO() as stream:
            builder.dump(stream)
            xml = stream.getvalue()

        for line in (
            '<testsuite file="sample-workflow.yaml" name="hello-world-" errors="1" skipped="1">',
            '<testcase name="T01" classname="." file="sample-workflow.yaml" line="1">',
            '<error message="Test error">Test error message</error>',
            '<testcase name="T03" classname=".kind" file="sample-workflow.yaml" line="2">',
            '<skipped message="Test skipped">Test skipped message</skipped>',
        ):
            assert line in xml

    def test_2(self):
        builder = JUnitOutputBuilder()
        builder.update(
            path=Path("sample-workflow.yaml"),
            content="",
            diagnoses=[
                {
                    "type": "failure",
                    "line": 6,
                    "column": 15,
                    "code": "T02",
                    "manifest": "hello-",
                    "loc": ("spec", "entrypoint"),
                    "summary": "Test failure",
                    "msg": "Test failure message",
                    "input": "hello",
                    "fix": "world",
                },
                {
                    "type": "failure",
                    "line": 6,
                    "column": 15,
                    "code": "T02",
                    "manifest": "hello-2-",
                    "loc": ("spec", "entrypoint"),
                    "summary": "Test failure",
                    "msg": "Test failure message",
                    "input": "hello",
                    "fix": "world",
                },
                {
                    "type": "invalid",
                    "line": 1,
                    "code": "T04",
                    "manifest": None,
                    "loc": (),
                },
            ],
        )

        with io.StringIO() as stream:
            builder.dump(stream)
            xml = stream.getvalue()

        for line in (
            '<testsuite file="sample-workflow.yaml" name="hello-" failures="1">',
            '<testcase name="T02" classname=".spec.entrypoint" file="sample-workflow.yaml" line="6">',
            '<failure message="Test failure">Test failure message</failure>',
            '<testsuite file="sample-workflow.yaml" name="hello-2-" failures="1">',
        ):
            assert line in xml

    def test_empty_1(self):
        builder = JUnitOutputBuilder()

        with io.StringIO() as stream:
            builder.dump(stream)
            xml = stream.getvalue()

        assert "<?xml version='1.0' encoding='utf-8'?>" in xml
        assert re.search(
            r'<testsuites timestamp="\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{6}\+\d{2}:\d{2}" name="tugboat" />',
            xml,
        )

    def test_empty_2(self):
        builder = JUnitOutputBuilder()

        builder.update(
            path=Path(__file__),
            content="",
            diagnoses=[],
        )

        with io.StringIO() as stream:
            builder.dump(stream)
            xml = stream.getvalue()

        assert "<?xml version='1.0' encoding='utf-8'?>" in xml
        assert re.search(
            r'<testsuites timestamp="\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{6}\+\d{2}:\d{2}" name="tugboat" />',
            xml,
        )
