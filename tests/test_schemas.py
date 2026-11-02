import decimal
import logging
from pathlib import Path

import frozendict
import pytest
import ruamel.yaml
from dirty_equals import IsInstance
from pydantic import BaseModel, TypeAdapter, ValidationError

from tugboat.schemas import (
    Artifact,
    CronWorkflow,
    Parameter,
    Step,
    Template,
    Workflow,
    WorkflowTemplate,
)
from tugboat.schemas.arguments import Arguments
from tugboat.schemas.basic import Dict
from tugboat.schemas.debug import DebugManifest
from tugboat.schemas.template.container import Quantity
from tugboat.schemas.workflow import WorkflowSpec

logger = logging.getLogger(__name__)


class TestArtifacts:

    def test_validate_pass(self):
        assert Artifact.model_validate({"name": "my-artifact"}) == IsInstance(Artifact)

    def test_validate_fail(self):
        with pytest.raises(ValidationError) as exc_info:
            Artifact.model_validate({"name": "my-artifact", "value": "foobar"})

        errors = exc_info.value.errors()
        assert errors == [
            {
                "type": "artifact_prohibited_value_field",
                "loc": ("value",),
                "msg": "Field 'value' is not a valid field for artifact. Use 'raw' artifact type instead.",
                "input": "foobar",
            }
        ]


class TestParameters:

    def test_validate_pass(self):
        assert isinstance(
            Parameter.model_validate({"name": "param", "value": "foobar"}), Parameter
        )
        assert isinstance(
            Parameter.model_validate({"name": "param", "value": True}), Parameter
        )
        assert isinstance(
            Parameter.model_validate({"name": "param", "value": None}), Parameter
        )

    def test_validate_fail(self):
        #
        with pytest.raises(ValidationError) as exc_info:
            Parameter.model_validate({"name": "param", "value": {}})

        errors = exc_info.value.errors()
        assert errors == [
            {
                "type": "parameter_value_type_error",
                "loc": ("value",),
                "msg": "",
                "input": {},
            }
        ]

        #
        with pytest.raises(ValidationError) as exc_info:
            Parameter.model_validate({"name": "param", "value": 123.456})

        errors = exc_info.value.errors()
        assert errors == [
            {
                "type": "parameter_value_type_error",
                "loc": ("value",),
                "msg": "",
                "input": pytest.approx(123.456),
            }
        ]


class TestArguments:

    def test_parameter_dict(self):
        args = Arguments.model_validate(
            {
                "parameters": [
                    {"name": "foo"},
                    {"name": "foo"},
                    {"name": "bar"},
                    {"name": ""},
                ]
            }
        )

        assert args.parameter_dict == {
            "foo": IsInstance(Parameter),
            "bar": IsInstance(Parameter),
        }

    def test_artifact_dict(self):
        args = Arguments.model_validate(
            {
                "artifacts": [
                    {"name": "foo"},
                    {"name": "foo"},
                    {"name": "bar"},
                    {"name": ""},
                ]
            }
        )

        assert args.artifact_dict == {
            "foo": IsInstance(Artifact),
            "bar": IsInstance(Artifact),
        }


class TestDict:

    def test_typed(self):
        class Model(BaseModel):
            data: Dict[str, int]

        m = Model.model_validate({"data": {"a": 1}})
        assert isinstance(m.data, frozendict.frozendict)
        assert m.model_dump() == {"data": {"a": 1}}

    def test_untyped(self):
        ta = TypeAdapter(Dict)
        assert ta.validate_python({"a": 1}) == {"a": 1}
        assert ta.validate_python({"foo": "bar"}) == {"foo": "bar"}

    def test_validation_error(self):
        ta = TypeAdapter(Dict[str, str])
        with pytest.raises(ValidationError):
            ta.validate_python({"a": 1})


class TestQuantity:

    def test_validate(self):
        ta = TypeAdapter(Quantity)

        assert ta.validate_python("100m").value == decimal.Decimal("0.1")
        assert ta.validate_python("128").value == 128
        assert ta.validate_python("128Ki").value == 131072
        assert ta.validate_python("100Mi").value == 104857600
        assert ta.validate_python("1.5Gi").value == 1610612736
        assert ta.validate_python("1Ti").value == 1099511627776
        assert ta.validate_python("1Pi").value == 1125899906842624
        assert ta.validate_python("1Ei").value == 1152921504606846976

        assert ta.validate_python("1E2").value == 100
        assert ta.validate_python("1e-1").value == decimal.Decimal("0.1")

        with pytest.raises(ValidationError):
            ta.validate_python("foo")
        with pytest.raises(ValidationError):
            ta.validate_python("-1Gi")

    def test_dunder(self):
        assert repr(Quantity("100Mi")) == "Quantity(100Mi)"
        assert str(Quantity("1.5Gi")) == "1.5Gi"
        assert isinstance(hash(Quantity("100Mi")), int)

    def test_compare(self):
        assert Quantity("100Mi") < Quantity("1Gi")
        assert Quantity("1500Mi") > Quantity("1Gi")
        assert Quantity("1024") == Quantity("1Ki")

        assert Quantity("1E2") >= Quantity("100")
        assert Quantity("1e-1") <= Quantity("0.1")

        with pytest.raises(TypeError):
            assert Quantity("1500Mi") != "1500Mi"


class TestTemplate:

    def test_step_dict(self):
        template = Template.model_validate(
            {
                "name": "test",
                "steps": [
                    [{"name": "foo"}],
                    [{"name": "foo"}, {"name": "bar"}],
                    [{"name": ""}],
                ],
            }
        )
        assert template.step_dict == {
            "foo": IsInstance(Step),
            "bar": IsInstance(Step),
        }


class TestResourceClaims:

    @pytest.mark.parametrize("model", [WorkflowSpec, Template])
    @pytest.mark.parametrize("source", ["resourceClaimName", "resourceClaimTemplateName"])
    def test_parse_claim(self, model, source):
        spec = model.model_validate(
            {"resourceClaims": [{"name": "accelerator", source: "device-claim"}]}
        )

        claim = spec.resourceClaims[0]
        assert claim.name == "accelerator"
        assert getattr(claim, source) == "device-claim"
        assert spec.model_dump(exclude_none=True)["resourceClaims"] == (
            {"name": "accelerator", source: "device-claim"},
        )
        hash(claim)

    @pytest.mark.parametrize("model", [WorkflowSpec, Template])
    @pytest.mark.parametrize(
        ("claim", "field", "error_type"),
        [
            ({"resourceClaimName": "device-claim"}, "name", "missing"),
            ({"name": 123}, "name", "string_type"),
            (
                {"name": "accelerator", "resourceClaimName": 123},
                "resourceClaimName",
                "string_type",
            ),
            (
                {"name": "accelerator", "resourceClaimTemplateName": 123},
                "resourceClaimTemplateName",
                "string_type",
            ),
            (
                {"name": "accelerator", "unknown": "value"},
                "unknown",
                "extra_forbidden",
            ),
        ],
    )
    def test_invalid_claim(self, model, claim, field, error_type):
        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"resourceClaims": [claim]})

        error = exc_info.value.errors()[0]
        assert error["loc"] == ("resourceClaims", 0, field)
        assert error["type"] == error_type


class TestWorkflow:

    def test_template_dict(self):
        wf = Workflow.model_validate(
            {
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "Workflow",
                "metadata": {"name": "test"},
                "spec": {
                    "templates": [
                        {"name": "foo"},
                        {"name": "foo"},
                        {"name": "bar"},
                        {"name": ""},
                    ]
                },
            }
        )

        assert wf.template_dict == {
            "foo": IsInstance(Template),
            "bar": IsInstance(Template),
        }


class TestParseManifest:

    def test_cron_workflow(self, stable_hooks):
        manifest = stable_hooks.parse_manifest(
            manifest={
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "CronWorkflow",
                "metadata": {"name": "test-cron-wf"},
                "spec": {
                    "schedule": "* * * * *",
                    "concurrencyPolicy": "Replace",
                    "startingDeadlineSeconds": 0,
                    "workflowSpec": {
                        "entrypoint": "date",
                        "templates": [
                            {
                                "name": "date",
                                "container": {
                                    "image": "alpine:3.6",
                                    "command": ["sh", "-c"],
                                    "args": ["date; sleep 90"],
                                },
                            }
                        ],
                    },
                },
            }
        )
        assert isinstance(manifest, CronWorkflow)

    def test_workflow(self, stable_hooks):
        manifest = stable_hooks.parse_manifest(
            manifest={
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "Workflow",
                "metadata": {"generateName": "hello-world-"},
                "spec": {
                    "entrypoint": "hello-world",
                    "templates": [
                        {
                            "name": "hello-world",
                            "container": {
                                "image": "busybox",
                                "command": ["echo"],
                                "args": ["hello world"],
                            },
                        }
                    ],
                },
            }
        )
        assert isinstance(manifest, Workflow)

    def test_workflow_template(self, stable_hooks):
        manifest = stable_hooks.parse_manifest(
            manifest={
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "WorkflowTemplate",
                "metadata": {"generateName": "hello-world-"},
                "spec": {
                    "entrypoint": "hello-world",
                    "templates": [
                        {
                            "name": "hello-world",
                            "container": {
                                "image": "busybox",
                                "command": ["echo"],
                                "args": ["hello world"],
                            },
                        }
                    ],
                },
            }
        )
        assert isinstance(manifest, WorkflowTemplate)

    def test_debug(self, stable_hooks):
        manifest = stable_hooks.parse_manifest(
            manifest={
                "apiVersion": "tugboat.example.com/v1",
                "kind": "Debug",
                "metadata": {"generateName": "test-"},
                "spec": {},
            }
        )
        assert isinstance(manifest, DebugManifest)


def test_with_argo_examples(subtests: pytest.Subtests, argo_example_dir: Path):
    """Make sure our schemas are valid for (almost) all examples from Argo."""
    workflow_binding_dir = argo_example_dir / "workflow-event-binding"
    EXCLUDES = {
        # k8s-patch-json-workflow.yaml: duplicate keys
        argo_example_dir / "k8s-patch-json-workflow.yaml",
        # github-path-filter-workflowtemplate: found parameter value in list type
        workflow_binding_dir / "github-path-filter-workflowtemplate.yaml",
    }

    yaml = ruamel.yaml.YAML()

    for path in argo_example_dir.glob("**/*.yaml"):
        if path in EXCLUDES:
            continue

        with path.open() as fd:
            for document in yaml.load_all(fd):
                match document["kind"]:
                    case "Workflow":
                        model = Workflow
                    case "WorkflowTemplate":
                        model = WorkflowTemplate
                    case "CronWorkflow":
                        model = CronWorkflow
                    case _:
                        continue

                with subtests.test(path=path, kind=document["kind"]):
                    manifest = model.model_validate(document)
                    hash(manifest)


class TestExecutorPlugins:
    @pytest.fixture
    def plugin(self):
        return {
            "metadata": {"name": "hello", "labels": {"app": "hello"}},
            "spec": {
                "sidecar": {
                    "automountServiceAccountToken": False,
                    "container": {
                        "name": "hello",
                        "image": "python:alpine",
                        "args": ["server.py"],
                        "env": [{"name": "PORT", "value": "4356"}],
                        "resources": {"requests": {"cpu": "100m"}},
                    },
                }
            },
        }

    @pytest.mark.parametrize("model", [Workflow, WorkflowTemplate, CronWorkflow])
    def test_consumers(self, model, plugin):
        spec = {"executorPlugins": [plugin]}
        manifest = model.model_validate(
            {
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": model.__name__,
                "metadata": {"name": "example"},
                "spec": {"workflowSpec": spec} if model is CronWorkflow else spec,
            }
        )
        workflow_spec = (
            manifest.spec.workflowSpec if model is CronWorkflow else manifest.spec
        )
        assert isinstance(workflow_spec.executorPlugins, tuple)
        parsed = workflow_spec.executorPlugins[0]
        assert parsed.spec.sidecar.container.env[0].value == "4356"
        assert parsed.model_dump(mode="json", exclude_unset=True) == plugin
        assert isinstance(hash(parsed), int)
        assert isinstance(hash(manifest), int)
        with pytest.raises(ValidationError, match="frozen"):
            parsed.spec.sidecar.automountServiceAccountToken = True

    def test_omission_and_empty_list(self, plugin):
        assert WorkflowSpec().executorPlugins is None
        assert "executorPlugins" not in WorkflowSpec().model_dump(exclude_unset=True)
        assert WorkflowSpec(executorPlugins=[]).executorPlugins == ()
        del plugin["spec"]["sidecar"]["automountServiceAccountToken"]
        parsed = WorkflowSpec.model_validate({"executorPlugins": [plugin]})
        sidecar = parsed.executorPlugins[0].spec.sidecar
        assert sidecar.automountServiceAccountToken is None
        assert "automountServiceAccountToken" not in sidecar.model_dump(exclude_unset=True)

    @pytest.mark.parametrize(
        ("path", "value", "error_type"),
        [
            (("metadata",), None, "missing"),
            (("spec",), None, "missing"),
            (("spec", "sidecar"), None, "missing"),
            (("spec", "sidecar", "container"), None, "missing"),
            (("spec", "sidecar", "automountServiceAccountToken"), [], "bool_type"),
            (("spec", "sidecar", "unknown"), True, "extra_forbidden"),
            (("spec", "sidecar", "container", "args"), {}, "tuple_type"),
        ],
    )
    def test_invalid_nested_input(self, plugin, path, value, error_type):
        target = plugin
        for key in path[:-1]:
            target = target[key]
        if error_type == "missing":
            del target[path[-1]]
        else:
            target[path[-1]] = value
        with pytest.raises(ValidationError) as exc_info:
            WorkflowSpec.model_validate({"executorPlugins": [plugin]})
        assert ("executorPlugins", 0, *path) == exc_info.value.errors()[0]["loc"]
        assert exc_info.value.errors()[0]["type"] == error_type

    def test_official_example(self, argo_example_dir):
        path = argo_example_dir / "workflow-level-executor-plugin.yaml"
        with path.open() as fd:
            document = ruamel.yaml.YAML().load(fd)
        # Template.plugin is not yet supported; validate the requested field alone.
        spec = WorkflowSpec.model_validate(
            {"executorPlugins": document["spec"]["executorPlugins"]}
        )
        assert spec.executorPlugins[0].spec.sidecar.container.image
        assert isinstance(hash(spec.executorPlugins[0]), int)
