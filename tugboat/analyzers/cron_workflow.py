from __future__ import annotations

import typing

from tugboat.analyzers.kubernetes import GENERATED_SUFFIX_LENGTH, check_resource_name
from tugboat.constraints import require_exactly_one
from tugboat.core import hookimpl

if typing.TYPE_CHECKING:
    from collections.abc import Iterator

    from tugboat.schemas import CronWorkflow
    from tugboat.types import Diagnosis


@hookimpl
def analyze(manifest: CronWorkflow) -> Iterator[Diagnosis]:
    # early escape if the manifest is not recognized
    if manifest.apiVersion != "argoproj.io/v1alpha1" or manifest.kind != "CronWorkflow":
        return

    # invoke checks
    yield from check_metadata(manifest)


# ----------------------------------------------------------------------------
# CronWorkflow analyzers
# ----------------------------------------------------------------------------

MAX_CRON_WORKFLOW_NAME_LENGTH = 52
"""
The maximum length of a CronWorkflow name.
Ref: https://github.com/argoproj/argo-workflows/blob/v3.5.6/workflow/validate/validate.go#L90-L93
"""


def check_metadata(workflow: CronWorkflow) -> Iterator[Diagnosis]:
    yield from require_exactly_one(
        model=workflow.metadata,
        loc=("metadata",),
        fields=["name", "generateName"],
    )

    if workflow.metadata.name:
        for diagnosis in check_resource_name(
            workflow.metadata.name, max_length=MAX_CRON_WORKFLOW_NAME_LENGTH
        ):
            diagnosis["loc"] = "metadata", "name"

            if diagnosis["code"] == "M009":
                diagnosis["code"] = "CW001"
                diagnosis["msg"] = (
                    f"""
                    The maximum length of a CronWorkflow name is {MAX_CRON_WORKFLOW_NAME_LENGTH} characters.

                    When a Workflow is created, Argo Workflows appends a timestamp to the CronWorkflow name.
                    Make sure the CronWorkflow name is short enough to fit the timestamp, or it may cause creation failures.
                    """
                )

            yield diagnosis

    if workflow.metadata.generateName:
        for diagnosis in check_resource_name(
            workflow.metadata.generateName,
            max_length=MAX_CRON_WORKFLOW_NAME_LENGTH,
            is_generate_name=True,
        ):
            diagnosis["loc"] = "metadata", "generateName"

            if diagnosis["code"] == "M009":
                diagnosis["code"] = "CW001"
                length = MAX_CRON_WORKFLOW_NAME_LENGTH - GENERATED_SUFFIX_LENGTH
                diagnosis["msg"] = (
                    f"""
                    The maximum length of a CronWorkflow generate name is {length} characters.

                    When a Workflow is created, Argo Workflows appends a timestamp to the CronWorkflow name.
                    Make sure the CronWorkflow name is short enough to fit the timestamp, or it may cause creation failures.
                    """
                )

            yield diagnosis
