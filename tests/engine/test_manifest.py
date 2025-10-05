from dirty_equals import IsPartialDict

from tugboat.core import hookimpl
from tugboat.engine.mainfest import (
    analyze_manifest,
    get_manifest_metadata,
    is_kubernetes_manifest,
)


def test_analyze_manifest_no_issue():
    diagnoses = analyze_manifest(
        {
            "apiVersion": "tugboat.example.com/v1",
            "kind": "Debug",
            "metadata": {"name": "test"},
            "spec": {},
        }
    )
    assert diagnoses == []


def test_analyze_manifest_picked(plugin_manager):
    class _Domain:
        @hookimpl(tryfirst=True)
        def analyze(manifest):
            yield {"code": "T01", "loc": (), "msg": "Test 1"}
            yield {"code": "T04", "loc": ("spec", "foo"), "msg": "Test 2"}
            yield {"code": "T02", "loc": ("spec", "foo"), "msg": "Test 3"}
            yield {"code": "T03", "loc": ("spec",)}

    plugin_manager.register(_Domain)

    diagnoses = analyze_manifest(
        {
            "apiVersion": "tugboat.example.com/v1",
            "kind": "Debug",
            "metadata": {"name": "test"},
            "spec": {},
        }
    )
    assert diagnoses == [
        {
            "code": "T01",
            "loc": (),
            "msg": "Test 1",
            "ctx": {
                "manifest": {
                    "kind": "debug.tugboat.example.com",
                    "name": "test",
                }
            },
        },
        {
            "code": "T03",
            "loc": ("spec",),
            "ctx": {
                "manifest": {
                    "kind": "debug.tugboat.example.com",
                    "name": "test",
                }
            },
        },
        IsPartialDict({"code": "T02"}),
        IsPartialDict({"code": "T04"}),
    ]


def test_analyze_manifest_not_k8s():
    diagnoses = analyze_manifest(
        {
            "foo": "bar",
        }
    )
    assert diagnoses == [
        {
            "type": "warning",
            "code": "M001",
            "loc": (),
            "summary": "Not a Kubernetes manifest",
            "msg": "The input does not look like a Kubernetes manifest",
        }
    ]


def test_analyze_manifest_manifest_validation_failed():
    diagnoses = analyze_manifest(
        {
            "apiVersion": "tugboat.example.com/v1",
            "kind": "Debug",
            "metadata": {"name": "test"},
            "spec": {
                "foo": "bar",
            },
        }
    )
    assert diagnoses == [
        {
            "code": "M102",
            "input": "foo",
            "loc": ("spec", "foo"),
            "msg": "Field 'foo' is not valid within the 'spec' section.",
            "summary": "Found redundant field",
            "type": "failure",
            "ctx": {
                "manifest": {
                    "kind": "debug.tugboat.example.com",
                    "name": "test",
                }
            },
        },
    ]


def test_analyze_manifest_manifest_error(plugin_manager):
    class _Domain:
        @hookimpl(tryfirst=True)
        def parse_manifest(manifest: dict):
            raise RuntimeError("Test exception")

    plugin_manager.register(_Domain)

    diagnoses = analyze_manifest(
        {
            "apiVersion": "v1",
            "kind": "ParseError",
        }
    )
    assert diagnoses == [
        IsPartialDict(
            {
                "type": "error",
                "code": "F001",
                "loc": (),
                "summary": "Internal error while analyzing manifest",
                "msg": "An error occurred while parsing the manifest: Test exception",
            }
        )
    ]


def test_analyze_manifest_unknown_manifest():
    diagnoses = analyze_manifest(
        {
            "apiVersion": "example.com/v1",
            "kind": "Unknown",
        }
    )
    assert diagnoses == [
        IsPartialDict(
            {
                "type": "warning",
                "code": "M002",
                "loc": (),
                "summary": "Unsupported manifest kind",
                "msg": "Manifest kind unknown.example.com is not supported",
            }
        )
    ]


def test_analyze_manifest_not_a_manifest_object(plugin_manager):
    class _Domain:
        @hookimpl(tryfirst=True)
        def parse_manifest(manifest: dict):
            return object()

    plugin_manager.register(_Domain)

    diagnoses = analyze_manifest(
        {
            "apiVersion": "v1",
            "kind": "ParseError",
        }
    )
    assert diagnoses == [
        IsPartialDict(
            {
                "type": "error",
                "code": "F001",
                "loc": (),
                "summary": "Internal error while analyzing manifest",
                "msg": "Expected a Manifest object, got <class 'object'>",
            }
        )
    ]


def test_analyze_manifest_analyze_error(plugin_manager):
    class _Domain:
        @hookimpl(tryfirst=True)
        def analyze(manifest):
            raise RuntimeError("Test exception")
            yield  # make this func a generator

    plugin_manager.register(_Domain)

    diagnoses = analyze_manifest(
        {
            "apiVersion": "tugboat.example.com/v1",
            "kind": "Debug",
            "metadata": {"name": "test"},
            "spec": {},
        }
    )
    assert diagnoses == [
        IsPartialDict(
            {
                "type": "error",
                "code": "F001",
                "loc": (),
                "summary": "Internal error while analyzing manifest",
                "msg": "An error occurred while analyzing the manifest: Test exception",
            }
        )
    ]


class TestAnalyzeManifest:

    @hookimpl(tryfirst=True)
    def analyze(self, manifest):
        if manifest.kind == "AnalysisError":
            raise RuntimeError("Test exception")

        yield {"code": "T01", "loc": (), "msg": "Test 1"}
        yield {"code": "T04", "loc": ("spec", "foo"), "msg": "Test 2"}
        yield {"code": "T02", "loc": ("spec", "foo"), "msg": "Test 3"}
        yield {
            "code": "T03",
            "loc": ("spec"),
            "msg": """
                Test 4. This is a long message that should be wrapped across
                multiple lines to test the formatting.
                """,
        }


class TestIsKubernetesManifest:

    def test(self):
        assert is_kubernetes_manifest({"apiVersion": "v1", "kind": "Pod"})
        assert not is_kubernetes_manifest({"apiVersion": "v1"})
        assert not is_kubernetes_manifest({"kind": "Pod"})
        assert not is_kubernetes_manifest({})
        assert not is_kubernetes_manifest({"foo": "bar"})


class TestGetManifestMetadata:

    def test_1(self):
        metadata = get_manifest_metadata(
            {
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "Workflow",
                "metadata": {"name": "my-workflow", "namespace": "my-namespace"},
            }
        )
        assert metadata == {
            "kind": "workflow.argoproj.io",
            "name": "my-workflow",
            "namespace": "my-namespace",
        }

    def test_2(self):
        metadata = get_manifest_metadata(
            {"apiVersion": "v1", "kind": "Pod", "metadata": {"generateName": "my-pod-"}}
        )
        assert metadata == {
            "kind": "pod",
            "name": "my-pod-",
        }

    def test_fallback(self):
        metadata = get_manifest_metadata({"apiVersion": "", "kind": ""})
        assert metadata == {
            "kind": "unknown.unknown",
        }
