import io
import logging

import colorlog
import pytest

from tugboat.console import setup_loggings


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
