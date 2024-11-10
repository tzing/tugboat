import logging
from collections.abc import Sequence
from pathlib import Path

import pytest
import ruamel.yaml
from pydantic import ValidationError

from tugboat.schemas import Workflow, WorkflowTemplate

logger = logging.getLogger(__name__)


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
