import io
import logging
import logging.handlers
import shutil
from pathlib import Path

import click.testing
import colorlog
import pytest

from tugboat.console.main import generate_report, main, setup_logging, summarize


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
        result = runner.invoke(main, [str(target)])

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
        result = runner.invoke(main)

        assert result.exit_code == 0
        assert "All passed!" in result.output

    @pytest.mark.usefixtures("_reset_logging")
    def test_no_yaml_found(self, tmp_path: Path):
        runner = click.testing.CliRunner()
        result = runner.invoke(main, [str(tmp_path)])

        assert result.exit_code == 1
        assert "No YAML file found" in result.output

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


class TestGenerateReport:
    def test_output_stream(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        def _mock_console_report(diagnostics, output_stream, color):
            output_stream.write("mock report")

        monkeypatch.setattr(
            "tugboat.console.outputs.console.report", _mock_console_report
        )

        output_file = tmp_path / "output.txt"

        generate_report({}, "console", output_file, None)

        assert output_file.read_text() == "mock report"

    def test_stdout_stream(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ):
        def _mock_console_report(diagnostics, output_stream, color):
            output_stream.write("mock report")

        monkeypatch.setattr(
            "tugboat.console.outputs.console.report", _mock_console_report
        )

        generate_report({}, "console", None, None)

        assert capsys.readouterr().out == "mock report"


class TestSummarize:
    def test_pass(self):
        assert summarize({}) == ("All passed!", False)

    def test_error_only(self):
        message, is_failed = summarize(
            {
                Path(__file__): [
                    {"type": "error"},
                ]
            }
        )
        assert message == "Found 1 errors"
        assert is_failed is True

    def test_failure_only(self):
        message, is_failed = summarize(
            {
                Path(__file__): [
                    {"type": "failure"},
                ]
            }
        )
        assert message == "Found 1 failures"
        assert is_failed is True

    def test_skipped_only(self):
        message, is_failed = summarize(
            {
                Path(__file__): [
                    {"type": "skipped"},
                    {"type": "skipped"},
                ]
            }
        )
        assert message == "Found 2 skipped checks"
        assert is_failed is False

    def test_mixed(self):
        message, is_failed = summarize(
            {
                Path(__file__): [
                    {"type": "error"},
                    {"type": "skipped"},
                ]
            }
        )
        assert message == "Found 1 errors, 1 skipped checks"
        assert is_failed is True
