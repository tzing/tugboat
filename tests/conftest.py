from pathlib import Path

import pytest

from tugboat.core import get_plugin_manager


@pytest.fixture(scope="session")
def argo_example_dir() -> Path:
    directory = Path(__file__).parent / "fixtures" / "argo-workflows" / "examples"
    if not directory.is_dir():
        pytest.skip("Argo examples directory not found")
    return directory


@pytest.fixture
def plugin_manager():
    get_plugin_manager.cache_clear()
    yield get_plugin_manager()
    get_plugin_manager.cache_clear()
