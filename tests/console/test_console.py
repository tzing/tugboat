import io
import logging
from pathlib import Path

import click
import click.testing
import colorlog
import pytest
from dirty_equals import IsInstance, IsList

from tugboat.console import setup_loggings, update_settings
from tugboat.settings import settings
from tugboat.types import GlobPath


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
