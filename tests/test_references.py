
import pytest

from tugboat.references import (
    get_global_context,
    get_step_context,
    get_template_context,
    get_workflow_context,
)
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

        ctx = get_workflow_context(workflow)
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


class TestTemplateContext:

    def test_container(self):
        workflow = Workflow.model_validate(
            {
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "Workflow",
                "metadata": {"generateName": "test-"},
                "spec": {
                    "templates": [
                        {
                            "name": "echo",
                            "inputs": {"parameters": [{"name": "message"}]},
                            "retryStrategy": {
                                "limit": 3,
                            },
                            "container": {
                                "image": "alpine:latest",
                                "command": ["sh", "-c"],
                                "args": [
                                    "echo {{inputs.parameters.message}} | tee {{output.parameters.foo.path}}"
                                ],
                            },
                            "outputs": {
                                "parameters": [
                                    {
                                        "name": "foo",
                                        "valueFrom": {"path": "/tmp/message.txt"},
                                    }
                                ],
                                "artifacts": [
                                    {"name": "bar", "path": "/tmp/message.txt"}
                                ],
                            },
                        },
                        {
                            "name": "hello-world",
                            "container": {
                                "image": "busybox",
                                "command": ["echo"],
                                "args": ["hello world"],
                            },
                        },
                    ],
                },
            }
        )
        assert workflow.spec.templates  # satisfy pyright

        ctx = get_template_context(workflow, workflow.spec.templates[0])
        assert ("workflow", "name") in ctx.parameters
        assert ("workflow", "status") in ctx.parameters
        assert ("retries",) in ctx.parameters
        assert ("inputs", "parameters", "message") in ctx.parameters
        assert ("outputs", "parameters", "foo", "path") in ctx.parameters
        assert ("outputs", "artifacts", "bar", "path") in ctx.parameters

        ctx = get_template_context(workflow, workflow.spec.templates[1])
        assert ("workflow", "name") in ctx.parameters
        assert ("retries",) not in ctx.parameters
        assert ("inputs", "parameters", "message") not in ctx.parameters

    def test_step(self):
        workflow = Workflow.model_validate(
            {
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "Workflow",
                "metadata": {"generateName": "loops-"},
                "spec": {
                    "entrypoint": "loop-example",
                    "templates": [
                        {
                            "name": "loop-example",
                            "steps": [
                                [
                                    {
                                        "name": "print-message-loop",
                                        "template": "print-message",
                                        "arguments": {
                                            "parameters": [
                                                {"name": "message", "value": "{{item}}"}
                                            ]
                                        },
                                        "withItems": ["hello world", "goodbye world"],
                                    },
                                    {
                                        "name": "extra-step",
                                        "templateRef": {
                                            "name": "demo",
                                            "template": "print-message",
                                        },
                                    },
                                ]
                            ],
                        },
                        {
                            "name": "print-message",
                            "inputs": {"parameters": [{"name": "message"}]},
                            "outputs": {"parameters": [{"name": "echo"}]},
                            "container": {
                                "image": "busybox",
                                "command": ["echo"],
                                "args": ["{{inputs.parameters.message}}"],
                            },
                        },
                    ],
                },
            }
        )
        assert workflow.spec.templates  # satisfy pyright

        ctx = get_template_context(workflow, workflow.spec.templates[0])
        assert ("workflow", "name") in ctx.parameters
        assert ("steps", "print-message-loop", "id") in ctx.parameters
        assert (
            "steps",
            "print-message-loop",
            "outputs",
            "parameters",
            "echo",
        ) in ctx.parameters
        assert (
            "steps",
            "extra-step",
            "outputs",
            "parameters",
            "WHATEVER",
        ) in ctx.parameters

        ctx = get_template_context(workflow, workflow.spec.templates[1])
        assert ("workflow", "name") in ctx.parameters
        assert ("steps", "print-message-loop", "id") not in ctx.parameters


class TestStepContext:

    def test(self):
        workflow = Workflow.model_validate(
            {
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "Workflow",
                "metadata": {"generateName": "loops-"},
                "spec": {
                    "templates": [
                        {
                            "steps": [
                                [
                                    {
                                        "name": "step-1",
                                        "withItems": [{"message": "hello world"}],
                                    },
                                    {
                                        "name": "step-2",
                                        "withParam": '[{"message": "hello world"}]',
                                    },
                                    {
                                        "name": "step-2",
                                        "withParam": "{{ inputs.parameters }}",
                                    },
                                ]
                            ],
                        },
                    ],
                },
            }
        )
        assert workflow.spec.templates

        (template,) = workflow.spec.templates
        assert template.steps

        step_1, step_2, step_3 = template.steps[0]

        ctx = get_step_context(workflow, template, step_1)
        assert ("inputs", "parameters") in ctx.parameters
        assert ("item",) in ctx.parameters
        assert ("item", "message") in ctx.parameters
        assert ("item", "foo") not in ctx.parameters

        ctx = get_step_context(workflow, template, step_2)
        assert ("item", "message") in ctx.parameters
        assert ("item", "foo") not in ctx.parameters

        ctx = get_step_context(workflow, template, step_3)
        assert ("item", "message") in ctx.parameters
        assert ("item", "foo") in ctx.parameters
