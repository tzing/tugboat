from __future__ import annotations

import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from tugboat.schemas.basic import Array
from tugboat.schemas.manifest import Manifest
from tugboat.schemas.workflow import WorkflowSpec

if os.getenv("DOCUTILSCONFIG"):
    __all__ = ["CronWorkflowSpec"]


class CronWorkflowSpec(BaseModel):
    """
    `CronWorkflowSpec`_ is the specification of a CronWorkflow.

    .. _CronWorkflowSpec: https://argo-workflows.readthedocs.io/en/latest/fields/#cronworkflowspec
    """

    model_config = ConfigDict(extra="forbid")

    concurrencyPolicy: str | None = None
    failedJobsHistoryLimit: int | None = None
    schedule: str | None = None
    schedules: Array[str] | None = None
    startingDeadlineSeconds: int | None = None
    successfulJobsHistoryLimit: int | None = None
    suspend: bool | None = None
    timezone: str | None = None
    when: str | None = None
    workflowSpec: WorkflowSpec

    stopStrategy: Any | None = None
    workflowMetadata: Any | None = None

    def __hash__(self):
        return hash((self.schedule, self.schedules, self.workflowSpec))


class CronWorkflow(Manifest[CronWorkflowSpec]):
    """
    `CronWorkflows`_ are workflows that run on a schedule.

    .. _CronWorkflows: https://argo-workflows.readthedocs.io/en/latest/cron-workflows/
    """

    apiVersion: Literal["argoproj.io/v1alpha1"]  # type: ignore[reportIncompatibleVariableOverride]
    kind: Literal["CronWorkflow"]  # type: ignore[reportIncompatibleVariableOverride]
    spec: CronWorkflowSpec
