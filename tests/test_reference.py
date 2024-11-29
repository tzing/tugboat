import pytest

from tugboat.reference import (
    Context,
    find_closest_match,
    get_global_context,
    get_workflow_context_c,
)
from tugboat.schemas import Workflow


class TestFindClosestMatch:

    @pytest.mark.parametrize(
        ("target", "expected"),
        [
            # exact match
            (("red", "pink"), ("red", "pink")),
            (("red", "teal", "pink"), ("red", "teal", "pink")),
            # length mismatch
            (("red", "pink", "EXTRA"), ("red", "pink")),
            (("red",), ("red", "blue")),
            # character mismatch
            (("red", "pinkk"), ("red", "pink")),
            (("red", "teel", "pink"), ("red", "teal", "pink")),
        ],
    )
    def test(self, target, expected):
        candidates = [
            ("red", "blue"),
            ("red", "pink"),
            ("red", "teal"),
            ("red", "blue", "pink"),
            ("red", "teal", "pink"),
            ("red", "blue", "pink", "gray"),
            ("red", "blue", "teal", "gray"),
        ]
        assert find_closest_match(target, candidates) == expected


class TestGetGlobalContext:

    def test(self):
        ctx = get_global_context()
        assert isinstance(ctx, Context)
        assert isinstance(ctx.parameters, set)
        assert all(isinstance(p, tuple) for p in ctx.parameters)
        assert isinstance(ctx.artifacts, set)
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
                            "name": "hello-world",
                            "container": {
                                "image": "busybox",
                                "command": ["echo"],
                                "args": ["hello world"],
                            },
                        },
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
