from pydantic import BaseModel

from tugboat.analyze import analyze_raw
from tugboat.core import hookimpl
from tugboat.schemas import Manifest


class TestAnalyzeRaw:
    @hookimpl(tryfirst=True)
    def parse_manifest(self, manifest: dict):
        if manifest.get("kind") == "Unrecognized":
            return
        if manifest.get("kind") == "NotManifest":
            return "Not a manifest object"
        if manifest.get("kind") == "ParseError":
            raise RuntimeError("Test exception")

        class Spec(BaseModel):
            foo: str

        class MockManifest(Manifest[Spec]): ...

        return MockManifest.model_validate(manifest)

    @hookimpl(tryfirst=True)
    def analyze(self, manifest):
        if manifest.kind == "AnalysisError":
            raise RuntimeError("Test exception")

        yield {"code": "T01", "loc": (), "msg": "Test 1"}
        yield {"code": "T04", "loc": ("spec", "foo"), "msg": "Test 2"}
        yield {"code": "T02", "loc": ("spec", "foo"), "msg": "Test 3"}
        yield {"code": "T03", "loc": ("spec"), "msg": "Test 4"}

    def test_success(self, plugin_manager):
        plugin_manager.register(self)

        diagnostics = analyze_raw(
            {
                "apiVersion": "v1",
                "kind": "Test",
                "metadata": {"name": "test"},
                "spec": {"foo": "bar"},
            }
        )
        assert diagnostics == [
            {"code": "T01", "loc": (), "msg": "Test 1"},
            {"code": "T03", "loc": ("spec"), "msg": "Test 4"},
            {"code": "T02", "loc": ("spec", "foo"), "msg": "Test 3"},
            {"code": "T04", "loc": ("spec", "foo"), "msg": "Test 2"},
        ]

    def test_parse_manifest_validation_error(self, plugin_manager):
        plugin_manager.register(self)

        diagnostics = analyze_raw(
            {
                "apiVersion": "v1",
                "kind": 1234,
                "metadata": {"name": "test"},
                "spec": {"foo": "bar"},
            }
        )
        assert diagnostics == [
            {
                "type": "failure",
                "code": "M001",
                "loc": ("kind",),
                "msg": "Input should be a valid string",
                "input": 1234,
            }
        ]

    def test_parse_manifest_exception(self, plugin_manager):
        plugin_manager.register(self)

        diagnostics = analyze_raw(
            {
                "apiVersion": "v1",
                "kind": "ParseError",
            }
        )
        assert diagnostics == [
            {
                "type": "error",
                "code": "E001",
                "loc": (),
                "summary": "Internal error while analyzing manifest",
                "msg": "An error occurred while parsing the manifest: Test exception",
            }
        ]

    def test_unrecognized_kind(self, plugin_manager):
        plugin_manager.register(self)

        diagnostics = analyze_raw(
            {
                "apiVersion": "v1",
                "kind": "Unrecognized",
            }
        )
        assert diagnostics == [
            {
                "type": "skipped",
                "code": "M002",
                "loc": (),
                "msg": "Manifest of kind 'Unrecognized' is not supported",
            }
        ]

    def test_not_manifest_obj(self, plugin_manager):
        plugin_manager.register(self)

        diagnostics = analyze_raw(
            {
                "apiVersion": "v1",
                "kind": "NotManifest",
            }
        )
        assert diagnostics == [
            {
                "type": "error",
                "code": "E001",
                "loc": (),
                "summary": "Internal error while analyzing manifest",
                "msg": "Expected a Manifest object, got <class 'str'>",
            }
        ]

    def test_analyze_error(self, plugin_manager):
        plugin_manager.register(self)

        diagnostics = analyze_raw(
            {
                "apiVersion": "v1",
                "kind": "AnalysisError",
                "metadata": {"generateName": "test-"},
                "spec": {"foo": "bar"},
            }
        )
        assert diagnostics == [
            {
                "type": "error",
                "code": "E001",
                "loc": (),
                "summary": "Internal error while analyzing manifest",
                "msg": "An error occurred while analyzing the manifest: Test exception",
            }
        ]
