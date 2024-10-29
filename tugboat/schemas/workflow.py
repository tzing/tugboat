from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from tugboat.schemas.arguments import Arguments
from tugboat.schemas.manifest import Manifest, Metadata
from tugboat.schemas.template import Template


class Workflow(Manifest):
    apiVersion: Literal["argoproj.io/v1alpha1"]  # type: ignore[reportIncompatibleVariableOverride]
    kind: Literal["Workflow"]  # type: ignore[reportIncompatibleVariableOverride]
    metadata: Metadata
    spec: Spec


class WorkflowTemplate(Workflow):
    kind: Literal["WorkflowTemplate"]  # type: ignore[reportIncompatibleVariableOverride]


class Spec(BaseModel):
    arguments: Arguments | None = None
    entrypoint: str | None = None
    templateDefaults: Template | None = None
    templates: list[Template] | None = None
    workflowTemplateRef: WorkflowTemplateRef | None = None


class WorkflowTemplateRef(BaseModel):

    model_config = ConfigDict(extra="forbid")

    name: str
    clusterScope: bool | None = None
