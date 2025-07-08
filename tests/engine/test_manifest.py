from tugboat.core import hookimpl
from tugboat.engine.mainfest import (
    analyze_manifest,
    get_manifest_kind_and_name,
    is_kubernetes_manifest,
    normalize_diagnosis,
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
            yield {
                "code": "T03",
                "loc": ("spec",),
                "msg": """
                    Test 4. This is a long message that should be wrapped across
                    multiple lines to test the formatting.
                    """,
            }

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
            "summary": "Test 1",
            "msg": "Test 1",
        },
        {
            "code": "T03",
            "loc": ("spec",),
            "summary": "Test 4",
            "msg": "Test 4. This is a long message that should be wrapped across\n"
            "multiple lines to test the formatting.",
        },
        {
            "code": "T02",
            "loc": ("spec", "foo"),
            "summary": "Test 3",
            "msg": "Test 3",
        },
        {
            "code": "T04",
            "loc": ("spec", "foo"),
            "summary": "Test 2",
            "msg": "Test 2",
        },
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
        {
            "type": "error",
            "code": "F001",
            "loc": (),
            "summary": "Internal error while analyzing manifest",
            "msg": "An error occurred while parsing the manifest: Test exception",
        }
    ]


def test_analyze_manifest_unknown_manifest():
    diagnoses = analyze_manifest(
        {
            "apiVersion": "example.com/v1",
            "kind": "Unknown",
        }
    )
    assert diagnoses == [
        {
            "type": "warning",
            "code": "M002",
            "loc": (),
            "summary": "Unsupported manifest kind",
            "msg": "Manifest kind example.com/Unknown is not supported",
        }
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
        {
            "type": "error",
            "code": "F001",
            "loc": (),
            "summary": "Internal error while analyzing manifest",
            "msg": "Expected a Manifest object, got <class 'object'>",
        }
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
        {
            "type": "error",
            "code": "F001",
            "loc": (),
            "summary": "Internal error while analyzing manifest",
            "msg": "An error occurred while analyzing the manifest: Test exception",
        }
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


class TestGetManifestKindAndName:

    def test_1(self):
        kind, name = get_manifest_kind_and_name(
            {
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "Workflow",
                "metadata": {"name": "my-workflow"},
            }
        )
        assert kind == "argoproj.io/Workflow"
        assert name == "my-workflow"

    def test_2(self):
        kind, name = get_manifest_kind_and_name(
            {"apiVersion": "v1", "kind": "Pod", "metadata": {"generateName": "my-pod-"}}
        )
        assert kind == "v1/Pod"
        assert name == "my-pod-"

    def test_fallback(self):
        kind, name = get_manifest_kind_and_name({"apiVersion": "", "kind": ""})
        assert kind == "unknown/Unknown"
        assert name == "<unknown>"


class TestNormalizeDiagnosis:

    def test_1(self):
        diagnosis = {
            "code": "T01",
            "loc": ["spec", "foo"],
            "msg": "Test 1. Some extra message.",
        }
        assert normalize_diagnosis(diagnosis) == {
            "code": "T01",
            "loc": ("spec", "foo"),
            "summary": "Test 1",
            "msg": "Test 1. Some extra message.",
        }

    def test_2(self):
        diagnosis = {
            "code": "T01",
            "loc": ("spec", "foo"),
            "msg": "Test 2 with \nnew line",
        }
        assert normalize_diagnosis(diagnosis) == {
            "code": "T01",
            "loc": ("spec", "foo"),
            "summary": "Test 2 with",
            "msg": "Test 2 with \nnew line",
        }

    def test_empty(self):
        diagnosis = {}
        assert normalize_diagnosis(diagnosis) == {
            "code": "F-D41D8C",
            "loc": (),
            "summary": "",
            "msg": "",
        }
