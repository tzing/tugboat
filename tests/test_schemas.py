import logging
from collections.abc import Sequence
from pathlib import Path

import frozendict
import pytest
import ruamel.yaml
from pydantic import BaseModel, TypeAdapter, ValidationError

from tugboat.schemas import CronWorkflow, Workflow, WorkflowTemplate
from tugboat.schemas.basic import Dict

logger = logging.getLogger(__name__)


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


class TestArgoExamples:
    """
    Make sure our schemas are valid for (almost) all examples from Argo.
    """

    def test_workflow(self, argo_example_dir: Path):
        manifests = load_manifests(
            dir_path=argo_example_dir,
            expected_kinds=["Workflow"],
            exclude_files=[
                # These manifests use deprecated `onExit` field
                "exit-handler-step-level.yaml",
                "template-on-exit.yaml",
                # webhdfs-input-output-artifacts.yaml: found `overwrite` field on artifact which is not documented
                "webhdfs-input-output-artifacts.yaml",
            ],
        )

        for file, resource in manifests:
            try:
                Workflow.model_validate(resource)
            except ValidationError:
                logger.exception("Failed to validate %s", file)
                pytest.fail(f"Failed to validate {file}")

    def test_workflowtemplate(self, argo_example_dir: Path):
        manifests = load_manifests(
            dir_path=argo_example_dir,
            expected_kinds=["WorkflowTemplate"],
        )

        for file, resource in manifests:
            try:
                WorkflowTemplate.model_validate(resource)
            except ValidationError:
                logger.exception("Failed to validate %s", file)
                pytest.fail(f"Failed to validate {file}")

    def test_cronworkflow(self, argo_example_dir: Path):
        manifests = load_manifests(
            dir_path=argo_example_dir,
            expected_kinds=["CronWorkflow"],
        )

        for file, resource in manifests:
            try:
                CronWorkflow.model_validate(resource)
            except ValidationError:
                logger.exception("Failed to validate %s", file)
                pytest.fail(f"Failed to validate {file}")


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
