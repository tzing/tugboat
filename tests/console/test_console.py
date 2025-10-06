import io
import logging
import shutil
from pathlib import Path

import click
import click.testing
import colorlog
import pytest
from dirty_equals import IsInstance, IsList

from tugboat.console import main, setup_loggings, update_settings
from tugboat.settings import settings
from tugboat.types import GlobPath


class TestMain:

    @pytest.mark.usefixtures("_reset_logging")
    def test_file_passed(self, fixture_dir: Path):
        target = fixture_dir / "sample-workflow.yaml"

        runner = click.testing.CliRunner()
        result = runner.invoke(main, [str(target), "--color"])

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

    @pytest.mark.skip(reason="temporary disabled")  # TODO
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


class TestSetupLoggings:

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
        setup_loggings(verbose_level)

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


class TestUpdateSettings:

    def test_1(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "foo").mkdir()
        (tmp_path / "bar").touch()

        update_settings(
            manifest=["*"],
            exclude=["bar"],
            follow_symlinks=False,
            color=True,
            output_format="junit",
        )

        assert settings.include == IsList(IsInstance(GlobPath))
        assert settings.exclude == IsList(IsInstance(Path))
        assert settings.color is True
        assert settings.follow_symlinks is False
        assert settings.output_format == "junit"

    def test_2(self):
        update_settings(
            manifest=[],
            exclude=[],
            follow_symlinks=None,
            color=None,
            output_format=None,
        )

        assert settings.include == []
        assert settings.exclude == []
        assert settings.color is None
        assert settings.follow_symlinks is False
        assert settings.output_format == "console"

    def test_errors(self):
        with pytest.raises(click.UsageError):
            update_settings(
                manifest=["/no/this/file"],
                exclude=[],
                follow_symlinks=None,
                color=None,
                output_format=None,
            )

        with pytest.raises(click.UsageError):
            update_settings(
                manifest=[],
                exclude=["/no/this/file"],
                follow_symlinks=None,
                color=None,
                output_format=None,
            )

        with pytest.raises(click.UsageError):
            update_settings(
                manifest=[],
                exclude=[],
                follow_symlinks="INVALID",
                color=None,
                output_format=None,
            )

        with pytest.raises(click.UsageError):
            update_settings(
                manifest=[],
                exclude=[],
                follow_symlinks=None,
                color="INVALID",
                output_format=None,
            )

        with pytest.raises(click.UsageError):
            update_settings(
                manifest=[],
                exclude=[],
                follow_symlinks=None,
                color=None,
                output_format="INVALID",
            )
