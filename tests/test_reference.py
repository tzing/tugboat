from tugboat.reference import Context, get_global_context, get_workflow_context_c
from tugboat.schemas import Workflow


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
