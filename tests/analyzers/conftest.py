import pytest

import tugboat.core


@pytest.fixture(scope="module")
def stable_hooks():
    pm = tugboat.core.get_plugin_manager()
    return pm.hook
