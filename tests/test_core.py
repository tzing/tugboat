import itertools
from collections.abc import Iterable
from unittest.mock import Mock

import pluggy

from tugboat.core import Diagnosis, get_plugin_manager, hookimpl
from tugboat.schemas import Manifest, Workflow


class TestPluginManager:
    def test(self):
        pm = get_plugin_manager()
        assert isinstance(pm, pluggy.PluginManager)


class TestHookspecs:
    @hookimpl(tryfirst=True)
    def parse_manifest(self, manifest: dict) -> Manifest | None:
        assert manifest == {"kind": "Mocked"}
        return Mock(Manifest)

    def test_parse_manifest(self, plugin_manager):
        plugin_manager.register(self)
        manifest = plugin_manager.hook.parse_manifest(manifest={"kind": "Mocked"})
        assert isinstance(manifest, Mock)

    @hookimpl(tryfirst=True)
    def analyze_workflow(self, workflow: Workflow) -> Iterable[Diagnosis]:
        assert isinstance(workflow, Workflow)
        yield {
            "code": "T01",
            "loc": (),
            "msg": "Mocked",
        }

    def test_analyze_workflow(self, plugin_manager):
        plugin_manager.register(self)

        iterators = plugin_manager.hook.analyze_workflow(workflow=Mock(Workflow))

        # REMINDER - pluggy collects hook results in a list
        assert isinstance(iterators, list)
        assert all(isinstance(it, Iterable) for it in iterators)

        diagnoses = itertools.chain.from_iterable(iterators)
        assert {
            "code": "T01",
            "loc": (),
            "msg": "Mocked",
        } in diagnoses
