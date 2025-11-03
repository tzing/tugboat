import decimal
import logging
from collections.abc import Sequence
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


class TestArgoExamples:
    """
    Make sure our schemas are valid for (almost) all examples from Argo.
    """

    def test_workflow(self, argo_example_dir: Path):
        manifests = load_manifests(
            dir_path=argo_example_dir,
            expected_kinds=["Workflow"],
        )

        for file, data in manifests:
            try:
                manifest = Workflow.model_validate(data)
            except ValidationError:
                logger.exception("Failed to validate %s", file)
                pytest.fail(f"Failed to validate {file}")

            try:
                hash(manifest)
            except TypeError:
                pytest.fail(f"Failed to hash {file}")

    def test_workflowtemplate(self, argo_example_dir: Path):
        manifests = load_manifests(
            dir_path=argo_example_dir,
            expected_kinds=["WorkflowTemplate"],
        )

        for file, data in manifests:
            try:
                manifest = WorkflowTemplate.model_validate(data)
            except ValidationError:
                logger.exception("Failed to validate %s", file)
                pytest.fail(f"Failed to validate {file}")

            try:
                hash(manifest)
            except TypeError:
                pytest.fail(f"Failed to hash {file}")

    def test_cronworkflow(self, argo_example_dir: Path):
        manifests = load_manifests(
            dir_path=argo_example_dir,
            expected_kinds=["CronWorkflow"],
        )

        for file, data in manifests:
            try:
                manifest = CronWorkflow.model_validate(data)
            except ValidationError:
                logger.exception("Failed to validate %s", file)
                pytest.fail(f"Failed to validate {file}")

            try:
                hash(manifest)
            except TypeError:
                pytest.fail(f"Failed to hash {file}")


def load_manifests(
    *, dir_path: Path, expected_kinds: list[str], exclude_files: Sequence[str] = ()
):
    yaml = ruamel.yaml.YAML()

    manifests = []
    for file_path in dir_path.glob("**/*.yaml"):
        if file_path.name in exclude_files:
            continue

        with file_path.open() as fd:
            for resource in yaml.load_all(fd):
                if resource["kind"] in expected_kinds:
                    logger.debug("Found %s in %s", resource["kind"], file_path)
                    manifests.append((file_path, resource))

    logger.critical("Found %d manifests of kind %s", len(manifests), expected_kinds)
    return manifests
