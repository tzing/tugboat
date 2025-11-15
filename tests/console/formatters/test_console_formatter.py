import io
import textwrap
from pathlib import Path

import pytest
from dirty_equals import DirtyEquals

import tugboat.settings
from tugboat.console.formatters import get_output_formatter
from tugboat.console.formatters.console import ConsoleFormatter, calc_highlight_range
from tugboat.engine import DiagnosisModel


class TestConsoleFormatter:

    def test_1(self, monkeypatch: pytest.MonkeyPatch, fixture_dir: Path):
        monkeypatch.setattr(tugboat.settings.settings, "output_format", "console")

        manifest_path = fixture_dir / "sample-workflow.yaml"

        formatter = get_output_formatter()
        formatter.update(
            content=manifest_path.read_text(),
            diagnoses=[
                DiagnosisModel.model_validate(
                    {
                        "type": "error",
                        "line": 1,
                        "column": 1,
                        "code": "T01",
                        "loc": (),
                        "msg": "Test error message\nwith details.",
                        "extras": {
                            "file": {
                                "filepath": "/path/to/sample-workflow.yaml",
                            },
                            "helm": {
                                "chart": "my-chart",
                                "template": "templates/workflow.yaml",
                            },
                            "manifest": {
                                "group": "example.com",
                                "kind": "Workflow",
                                "name": "hello-world-",
                            },
                        },
                    }
                )
            ],
        )

        with io.StringIO() as buffer:
            formatter.dump(buffer)
            report = buffer.getvalue()

        assert report == IsOutputEqual(
            """\
            T01 Test error message
              @/path/to/sample-workflow.yaml:1:1 (hello-world-)
              @Template:templates/workflow.yaml

              1 | apiVersion: argoproj.io/v1alpha1
                | └ T01 at $
              2 | kind: Workflow
              3 | metadata:

              Test error message
              with details.

            """
        ), f"Output:\n{report}"

    def test_2(self, fixture_dir: Path):
        manifest_path = fixture_dir / "missing-script-source.yaml"

        formatter = ConsoleFormatter()
        formatter.update(
            content=manifest_path.read_text(),
            diagnoses=[
                DiagnosisModel.model_validate(
                    {
                        "type": "failure",
                        "line": 10,
                        "column": 9,
                        "code": "T02",
                        "loc": ("spec", "templates", 0, "script"),
                        "summary": "Missing required field",
                        "msg": "Field 'source' is required but missing",
                        "fix": "foobar",
                        "extras": {
                            "file": {
                                "filepath": "/path/to/sample-workflow.yaml",
                            },
                            "manifest": {
                                "group": "argoproj.io",
                                "kind": "Workflow",
                                "name": "hello-",
                            },
                        },
                    }
                )
            ],
        )

        with io.StringIO() as buffer:
            formatter.dump(buffer)
            report = buffer.getvalue()

        assert report == IsOutputEqual(
            """\
            T02 Missing required field
              @/path/to/sample-workflow.yaml:10:9 (hello-)

               8 |     - name: hello
               9 |       script:
              10 |         image: alpine:latest
                 |         └ T02 at $.spec.templates[0].script

              Field 'source' is required but missing

              Do you mean: foobar

            """
        ), f"Output:\n{report}"

    def test_3(self, fixture_dir: Path):
        manifest_path = fixture_dir / "sample-workflow.yaml"

        formatter = ConsoleFormatter()
        formatter.update(
            content=manifest_path.read_text(),
            diagnoses=[
                DiagnosisModel.model_validate(
                    {
                        "type": "warning",
                        "line": 10,
                        "column": 15,
                        "code": "T03",
                        "loc": ("spec", "templates", 0, "container", "image"),
                        "msg": "Test warning message",
                        "input": "busybox",
                        "fix": '{\n  "image": "busybox",\n  "tag": "latest"\n}',
                    }
                )
            ],
        )

        with io.StringIO() as buffer:
            formatter.dump(buffer)
            report = buffer.getvalue()

        assert report == IsOutputEqual(
            """\
            T03 Test warning message
              @:10:15

               8 |     - name: hello-world
               9 |       container:
              10 |         image: busybox
                 |                ^^^^^^^
                 |                └ T03 at $.spec.templates[0].container.image
              11 |         command: [echo]
              12 |         args: ["hello world"]

              Test warning message

              Do you mean: |-
              {
                "image": "busybox",
                "tag": "latest"
              }

            """
        ), f"Output:\n{report}"


class IsOutputEqual(DirtyEquals[str]):

    def __init__(self, text: str):
        text = textwrap.dedent(text).rstrip(" ")
        super().__init__(text)
        self.text = text

    def equals(self, other):
        return self.text == other


class TestCalcHighlightRange:

    def test_success(self):
        assert calc_highlight_range("hello user 1234", 0, 1234) == (11, 15)

    def test_not_found(self):
        assert calc_highlight_range("hello world", 2, "hello") is None
        assert calc_highlight_range("hello world", 0, "not-found") is None

    def test_empty(self):
        assert calc_highlight_range("hello world", 0, " ") is None

    def test_none(self):
        assert calc_highlight_range("hello world; None", 0, None) is None
