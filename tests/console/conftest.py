import logging

import pytest


@pytest.fixture
def _reset_logging():
    yield
    for logger in (logging.root, logging.getLogger("tugboat")):
        logger.setLevel(logging.NOTSET)
        logger.propagate = True
        logger.handlers.clear()
