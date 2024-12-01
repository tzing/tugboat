import pytest

from tugboat.references import get_global_context, get_workflow_context_c
from tugboat.references.cache import LruDict, cache
from tugboat.references.context import AnyStr, Context, ReferenceCollection
from tugboat.schemas import Workflow


class TestReferenceCollection:

    def test(self):
        collection = ReferenceCollection()
        assert len(collection) == 0

        collection |= {
            ("a", "b"),
            ("c", AnyStr),
        }
        assert len(collection) == 2

        assert ("a", "b") in collection
        assert ("c", "SOMETHING-ELSE") in collection

        assert repr(collection) == "{('a', 'b'), ('c', ANY)}"

    def test_errors(self):
        collection = ReferenceCollection()
        with pytest.raises(TypeError):
            collection.add("not-a-tuple")
        with pytest.raises(NotImplementedError):
            collection.discard(("a", "b"))

    @pytest.mark.parametrize(
        ("target", "expected"),
        [
            # exact match
            (("red", "pink"), ("red", "pink")),
            (("red", "teal", "pink"), ("red", "teal", "pink")),
            # length mismatch
            (("red", "pink", "EXTRA"), ("red", "pink")),
            (("green",), ("green", "yellow")),
            # character mismatch
            (("red", "pinkk"), ("red", "pink")),
            (("red", "teel", "pink"), ("red", "teal", "pink")),
            # match `AnyStr`
            (("green", "grey", "WHATEVER"), ("green", "grey", "WHATEVER")),
            (("green", "grey", "WHATEVER", "SUB"), ("green", "grey", "WHATEVER")),
            (("green", "grey"), ("green", "yellow")),
        ],
    )
    def test_find_closest(self, target, expected):
        collection = ReferenceCollection()
        collection |= {
            ("red", "blue"),
            ("red", "pink"),
            ("red", "blue", "pink"),
            ("red", "teal", "pink"),
            ("red", "blue", "pink", "gray"),
            ("red", "blue", "teal", "gray"),
            ("green", "yellow"),
            ("green", "grey", AnyStr),
        }
        assert collection.find_closest(target) == expected

    def test_empty(self):
        collection = ReferenceCollection()
        assert collection.find_closest(("foo", "bar")) == ()
        assert collection.find_closest(()) == ()


class TestLruDict:
    def test_basic(self):
        d = LruDict(max_size=3)
        d["a"] = 1
        d["b"] = 2
        d["c"] = 3
        assert d == {"a": 1, "b": 2, "c": 3}

    def test_exceed_max_size(self):
        d = LruDict(max_size=3)
        d["a"] = 1
        d["b"] = 2
        d["c"] = 3
        d["d"] = 4
        assert d == {"b": 2, "c": 3, "d": 4}

    def test_update(self):
        d = LruDict(max_size=3)
        d["a"] = 1
        d["b"] = 2
        d["c"] = 3
        d["b"] = 4
        assert list(d.items()) == [
            ("a", 1),
            ("c", 3),
            ("b", 4),
        ]

    def test_get(self):
        d = LruDict(max_size=3)
        d["a"] = 1
        d["b"] = 2
        d["c"] = 3
        assert d.get("a") == 1
        assert d.get("not-exists") is None
        assert list(d.items()) == [
            ("b", 2),
            ("c", 3),
            ("a", 1),
        ]

    def test_del(self):
        d = LruDict(max_size=3)
        d["a"] = 1
        d["b"] = 2
        d["c"] = 3
        del d["b"]
        assert d == {"a": 1, "c": 3}


class TestCache:

    def test(self):
        @cache(4)
        def func(obj):
            ctx = Context()
            ctx.parameters |= {("foo", "bar")}
            return ctx

        ctx_1 = func(object())
        ctx_1.parameters |= {("baz", "qux")}
        assert len(ctx_1.parameters) == 2

        ctx_2 = func(object())
        assert len(ctx_2.parameters) == 1


class TestGetGlobalContext:

    def test(self):
        ctx = get_global_context()
        assert isinstance(ctx, Context)
        assert all(isinstance(p, tuple) for p in ctx.parameters)
        assert all(isinstance(a, tuple) for a in ctx.artifacts)

    def test_cache(self):
        assert get_global_context() == get_global_context()

        ctx_a = get_global_context()
        ctx_a.parameters |= {("mutation", "name")}

        ctx_b = get_global_context()
        assert ctx_a != ctx_b

        assert get_global_context() == get_global_context()


class TestGetWorkflowContext:

    def test(self):
        workflow = Workflow.model_validate(
            {
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "Workflow",
                "metadata": {"generateName": "test-"},
                "spec": {
                    "arguments": {
                        "parameters": [
                            {"name": "hello", "value": "world"},
                        ],
                        "artifacts": [
                            {"name": "art", "path": "/tmp/art.txt"},
                        ],
                    },
                    "templates": [
                        {
                            "name": "global-output",
                            "container": {
                                "image": "alpine:3.7",
                                "command": ["sh", "-c"],
                                "args": [
                                    "sleep 1; echo -n hello world > /tmp/hello_world.txt"
                                ],
                            },
                            "outputs": {
                                "parameters": [
                                    {
                                        "name": "hello-param",
                                        "valueFrom": {"path": "/tmp/hello_world.txt"},
                                        "globalName": "my-global-param",
                                    }
                                ],
                                "artifacts": [
                                    {
                                        "name": "hello-art",
                                        "path": "/tmp/hello_world.txt",
                                        "globalName": "my-global-art",
                                    }
                                ],
                            },
                        },
                    ],
                },
            }
        )

        ctx = get_workflow_context_c(workflow)
        assert isinstance(ctx, Context)

        assert ("workflow", "name") in ctx.parameters
        assert ("workflow", "parameters", "hello") in ctx.parameters
        assert (
            "workflow",
            "outputs",
            "parameters",
            "my-global-param",
        ) in ctx.parameters

        assert ("workflow", "outputs", "artifacts", "my-global-art") in ctx.artifacts
