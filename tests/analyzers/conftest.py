import logging

import pytest
from pydantic import TypeAdapter

from tugboat.engine import DiagnosisModel

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def diagnoses_logger():

    ta = TypeAdapter(list[DiagnosisModel])

    def _log(diagnoses: list[DiagnosisModel]):
        logger.critical(
            "Diagnoses: %s",
            ta.dump_json(
                diagnoses,
                indent=2,
                exclude_none=True,
                exclude_unset=True,
            ).decode(),
        )

    return _log
