import io
import logging
import logging.handlers
import shutil
from pathlib import Path

import click.testing
import colorlog
import pytest

from tugboat.console.main import DiagnosesCounter, main, setup_logging


@pytest.fixture
def _reset_logging():
    yield
    for logger in (logging.root, logging.getLogger("tugboat")):
        logger.setLevel(logging.NOTSET)
        logger.propagate = True
        logger.handlers.clear()


class TestMain:
    @pytest.mark.usefixtures("_reset_logging")
    def test_file_passed(self, fixture_dir: Path):
        target = fixture_dir / "sample-workflow.yaml"

        runner = click.testing.CliRunner()
        result = runner.invoke(main, [str(target), "--color", "1"])

        assert result.exit_code == 0
        assert "All passed!" in result.output

    @pytest.mark.usefixtures("_reset_logging")
    def test_file_picked(self, fixture_dir: Path):
        target = fixture_dir / "missing-script-source.yaml"

        runner = click.testing.CliRunner()
        result = runner.invoke(main, [str(target)])

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

        assert result.exit_code == 0
        assert "All passed!" in result.output

    @pytest.mark.usefixtures("_reset_logging")
    def test_stdin(self):
        runner = click.testing.CliRunner()
        result = runner.invoke(
            main,
            ["-"],
            input=(
                """
                apiVersion: argoproj.io/v1alpha1
                kind: Workflow
                metadata:
                  generateName: hello-world-
                spec:
                  entrypoint: hello-world
                  templates:
                    - name: hello-world
                      container:
                        image: busybox
                        command: [echo]
                        args: ["hello world"]
                """
            ),
        )
        assert result.exit_code == 0
        assert "All passed!" in result.output

    @pytest.mark.usefixtures("_reset_logging")
    def test_mixed_input_source(self, tmp_path: Path):
        runner = click.testing.CliRunner()
        result = runner.invoke(main, ["-", str(tmp_path)])
        assert result.exit_code == 2
        assert (
            "This option is only available when specified solely via the command line."
            in result.output
        )

    @pytest.mark.usefixtures("_reset_logging")
    def test_no_yaml_found(self, tmp_path: Path):
        runner = click.testing.CliRunner()
        result = runner.invoke(main, [str(tmp_path)])

        assert result.exit_code == 2
        assert "No manifest found." in result.output

    @pytest.mark.usefixtures("_reset_logging")
    def test_read_file_error(self, tmp_path: Path):
        target = tmp_path / "invalid.txt"
        target.write_bytes(b"\xa0Invalid Content")

        runner = click.testing.CliRunner()
        result = runner.invoke(main, [str(target)])

        assert result.exit_code == 1
        assert "Failed to read file" in result.output


class TestSetupLogging:

    @pytest.mark.parametrize(
        ("verbose_level", "has_err", "has_inf", "has_deb", "has_ext"),
        [
            (0, True, False, False, False),
            (1, True, True, False, False),
            (2, True, True, True, False),
            (3, True, True, True, True),
        ],
    )
    @pytest.mark.usefixtures("_reset_logging")
    def test(
        self,
        monkeypatch: pytest.MonkeyPatch,
        verbose_level: int,
        has_err: bool,
        has_inf: bool,
        has_deb: bool,
        has_ext: bool,
    ):
        # setup mock
        mock_handler = colorlog.StreamHandler(io.StringIO())

        def _mock_stream_handler(stream=None):
            return mock_handler

        monkeypatch.setattr("colorlog.StreamHandler", _mock_stream_handler)

        # setup logging
        setup_logging(verbose_level)

        # write logs
        logger = logging.getLogger("tugboat.sample")
        logger.error("ERR: Sample tugboat error message")
        logger.info("INF: Sample tugboat info message")
        logger.debug("DEB: Sample tugboat debug message")

        logger = logging.getLogger("external.sample")
        logger.info("EXT: Sample external info message")

        # check
        err = mock_handler.stream.getvalue()
        assert ("ERR" in err) == has_err
        assert ("INF" in err) == has_inf
        assert ("DEB" in err) == has_deb
        assert ("EXT" in err) == has_ext


class TestDiagnosesCounter:

    def test_pass(self):
        counter = DiagnosesCounter()
        assert counter.summary() == "All passed!"
        assert not counter.has_any_error()

    def test_errors(self):
        counter = DiagnosesCounter(["error"])
        assert counter.summary() == "Found 1 errors"
        assert counter.has_any_error()

    def test_failures(self):
        counter = DiagnosesCounter(["failure"])
        assert counter.summary() == "Found 1 failures"
        assert counter.has_any_error()

    def test_skipped(self):
        counter = DiagnosesCounter(["skipped"])
        assert counter.summary() == "Found 1 skipped checks"
        assert not counter.has_any_error()

    def test_mixed(self):
        counter = DiagnosesCounter()
        counter["error"] += 1
        counter["error"] += 1
        counter["failure"] += 1
        counter["skipped"] += 1
        assert counter.summary() == "Found 2 errors, 1 failures and 1 skipped checks"
        assert counter.has_any_error()
