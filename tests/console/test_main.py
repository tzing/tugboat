import io
import logging
import shutil
from pathlib import Path

import click.testing
import colorlog
import pytest

from tugboat.console.main import DiagnosesCounter, main


class TestMain:

    @pytest.mark.usefixtures("_reset_logging")
    def test_file_passed(self, fixture_dir: Path):
        target = fixture_dir / "sample-workflow.yaml"

        runner = click.testing.CliRunner()
        result = runner.invoke(main, [str(target), "--color", "1"])

        assert not result.exception
        assert result.exit_code == 0
        assert "All passed!" in result.output

    @pytest.mark.usefixtures("_reset_logging")
    def test_file_picked(self, fixture_dir: Path):
        target = fixture_dir / "missing-script-source.yaml"

        runner = click.testing.CliRunner()
        result = runner.invoke(main, [str(target)])

        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2
        assert "Found 1 failures" in result.output

    @pytest.mark.usefixtures("_reset_logging")
    def test_dir(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fixture_dir: Path
    ):
        monkeypatch.chdir(tmp_path)
        shutil.copy(fixture_dir / "sample-workflow.yaml", tmp_path / "workflow.yaml")

        runner = click.testing.CliRunner()
        result = runner.invoke(
            main,
            [
                "--output-format",
                "junit",
                "--follow-symlinks",
                str(tmp_path),
                "--output-file",
                str(tmp_path / "output.xml"),
            ],
        )

        assert not result.exception
        assert result.exit_code == 0
        assert "All passed!" in result.output

    @pytest.mark.usefixtures("_reset_logging")
    def test_stdin(self):
        runner = click.testing.CliRunner()
        result = runner.invoke(
            main,
            input="""
                apiVersion: tugboat.example.com/v1
                kind: Debug
                metadata:
                    generateName: test-
                spec: {}
                """,
        )

        assert not result.exception
        assert result.exit_code == 0
        assert "All passed!" in result.output

    @pytest.mark.usefixtures("_reset_logging")
    def test_no_yaml_found(self, tmp_path: Path):
        runner = click.testing.CliRunner()
        result = runner.invoke(main, [str(tmp_path)])

        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2
        assert "No manifest found." in result.output

    @pytest.mark.usefixtures("_reset_logging")
    def test_read_file_error(self, tmp_path: Path):
        target = tmp_path / "invalid.txt"
        target.write_bytes(b"\xa0Invalid Content")

        runner = click.testing.CliRunner()
        result = runner.invoke(main, [str(target)])

        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 1
        assert "Failed to read file" in result.output
