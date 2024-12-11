import io
from pathlib import Path

import pytest

from tugboat.console.outputs.console import _calc_highlight_range, report


class TestReport:

    def test_empty(self):
        with io.StringIO() as stream:
            report({}, stream, None)
            assert stream.getvalue() == ""

        with io.StringIO() as stream:
            report({Path(__file__): []}, stream, None)
            assert stream.getvalue() == ""

    def test_error(self, monkeypatch: pytest.MonkeyPatch, fixture_dir: Path):
        monkeypatch.chdir(fixture_dir)
        diagnoses = {
            Path("sample-workflow.yaml"): [
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
                }
            ]
        }

        with io.StringIO() as stream:
            report(diagnoses, stream, False)
            output = stream.getvalue()

        assert output.splitlines() == [
            "sample-workflow.yaml:1:1: T01 Test error",
            "",
            " 1 | apiVersion: argoproj.io/v1alpha1",
            "   | └ T01 at . in hello-world-",
            " 2 | kind: Workflow",
            " 3 | metadata:",
            "",
            "   Test error message",
            "",
        ]

    def test_failure(self, monkeypatch: pytest.MonkeyPatch, fixture_dir: Path):
        monkeypatch.chdir(fixture_dir)

        diagnoses = {
            Path("missing-script-source.yaml"): [
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
                }
            ]
        }

        with io.StringIO() as stream:
            report(diagnoses, stream, False)
            output = stream.getvalue()

        assert output.splitlines() == [
            "missing-script-source.yaml:6:15: T02 Test failure",
            "",
            " 4 |   generateName: hello-",
            " 5 | spec:",
            " 6 |   entrypoint: hello",
            "   |               ^^^^^",
            "   |               └ T02 at .spec.entrypoint in hello-",
            " 7 |   templates:",
            " 8 |     - name: hello",
            "",
            "   Test failure message",
            "",
            "   Do you mean: world",
            "",
        ]

    def test_skipped(self, monkeypatch: pytest.MonkeyPatch, fixture_dir: Path):
        monkeypatch.chdir(fixture_dir)
        diagnoses = {
            Path("sample-workflow.yaml"): [
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
                }
            ]
        }

        with io.StringIO() as stream:
            report(diagnoses, stream, False)
            output = stream.getvalue()

        assert output.splitlines() == [
            "sample-workflow.yaml:2:1: T03 Test skipped",
            "",
            " 1 | apiVersion: argoproj.io/v1alpha1",
            " 2 | kind: Workflow",
            "   | └ T03 at .kind in hello-world-",
            " 3 | metadata:",
            " 4 |   generateName: hello-world-",
            "",
            "   Test skipped message",
            "",
        ]

    @pytest.mark.parametrize(
        "diagnostic_type", ["failure", "error", "skipped", "INVALID"]
    )
    def test_colored(
        self, monkeypatch: pytest.MonkeyPatch, fixture_dir: Path, diagnostic_type: str
    ):
        """
        Just for make sure the process is working.
        The actual color or the output is not tested.
        """
        monkeypatch.chdir(fixture_dir)
        diagnoses = {
            Path("sample-workflow.yaml"): [
                {
                    "type": diagnostic_type,
                    "line": 1,
                    "column": 1,
                    "code": "T04",
                    "manifest": "hello-world-",
                    "loc": ("kind",),
                    "summary": "Test message",
                    "msg": "Test message",
                    "input": None,
                    "fix": None,
                }
            ]
        }

        with io.StringIO() as stream:
            report(diagnoses, stream, False)
            output = stream.getvalue()

        assert isinstance(output, str)


class TestCalcHighlightRange:

    def test_success(self):
        start, end = _calc_highlight_range("hello user 1234", 0, 1234)
        assert start == 11
        assert end == 15

    def test_not_found(self):
        assert _calc_highlight_range("hello world", 2, "hello") is None
        assert _calc_highlight_range("hello world", 0, "not-found") is None

    def test_empty(self):
        assert _calc_highlight_range("hello world", 0, " ") is None

    def test_none(self):
        assert _calc_highlight_range("hello world; None", 0, None) is None
