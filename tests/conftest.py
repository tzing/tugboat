from pathlib import Path

import pytest

from tugboat.core import get_plugin_manager


@pytest.fixture(scope="session")
def fixture_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def argo_example_dir(fixture_dir: Path) -> Path:
    directory = fixture_dir / "argo-workflows" / "examples"
    if not directory.is_dir():
        pytest.skip("Argo examples directory not found")
    return directory


@pytest.fixture(scope="session")
def argo_example_helm_dir(fixture_dir: Path) -> Path:
    directory = fixture_dir / "argo-workflows-example-helm"
    if not directory.is_dir():
        pytest.skip("Argo Helm examples directory not found")
    return directory


@pytest.fixture
def plugin_manager():
    get_plugin_manager.cache_clear()
    yield get_plugin_manager()
    get_plugin_manager.cache_clear()


@pytest.fixture(scope="class")
def stable_hooks():
    pm = get_plugin_manager()
    return pm.hook
