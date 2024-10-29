from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def argo_example_dir() -> Path:
    directory = Path(__file__).parent / "fixtures" / "argo-workflows" / "examples"
    if not directory.is_dir():
        pytest.skip("Argo examples directory not found")
    return directory
