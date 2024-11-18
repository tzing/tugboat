from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from tugboat.schemas.arguments import Arguments
from tugboat.schemas.manifest import Manifest, Metadata
from tugboat.schemas.template import Template
from tugboat.schemas.workflow import WorkflowSpec


class CronWorkflowSpec(BaseModel):
    """
    `CronWorkflowSpec`_ is the specification of a CronWorkflow.

    .. _CronWorkflowSpec: https://argo-workflows.readthedocs.io/en/latest/fields/#cronworkflowspec
    """

    model_config = ConfigDict(extra="forbid")

    schedule: str | None = None
    schedules: list[str] | None = None
    workflowSpec: WorkflowSpec

    # acknowledged fields
    concurrencyPolicy: str | None = None
    failedJobsHistoryLimit: int | None = None
    startingDeadlineSeconds: int | None = None
    stopStrategy: Any | None = None
    successfulJobsHistoryLimit: int | None = None
    suspend: bool | None = None
    timezone: str | None = None
    when: str | None = None
    workflowMetadata: Any | None = None


class CronWorkflow(Manifest[CronWorkflowSpec]):
    """
    `CronWorkflows`_ are workflows that run on a schedule.

    .. _CronWorkflow: https://argo-workflows.readthedocs.io/en/latest/cron-workflows/
    """

    apiVersion: Literal["argoproj.io/v1alpha1"]  # type: ignore[reportIncompatibleVariableOverride]
    kind: Literal["CronWorkflow"]  # type: ignore[reportIncompatibleVariableOverride]
