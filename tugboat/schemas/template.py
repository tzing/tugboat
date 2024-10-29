from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from tugboat.schemas.arguments import Arguments


class Template(BaseModel):
    """
    `Template`_ is a reusable and composable unit of execution in a workflow.

    .. _Template: https://argo-workflows.readthedocs.io/en/latest/fields/#template
    """

    name: str | None = None
    container: ContainerTemplate | None = None
    inputs: Arguments | None = None
    outputs: Arguments | None = None
    script: ScriptTemplate | None = None
    steps: list[list[Step]] | None = None


# ----------------------------------------------------------------------------
# container / script
# ----------------------------------------------------------------------------
class _ContainerEntry(BaseModel):
    image: str

    args: list[str] | None = None
    command: list[str] | None = None
    imagePullPolicy: Literal["Always", "Never", "IfNotPresent"] | None = None
    workingDir: str | None = None


class ContainerTemplate(_ContainerEntry):
    """
    A single application `container`_ that you want to run within a pod.

    .. _container: https://argo-workflows.readthedocs.io/en/latest/fields/#container
    """


class ScriptTemplate(_ContainerEntry):
    """
    `ScriptTemplate`_ is a template subtype to enable scripting through code steps.

    .. _ScriptTemplate: https://argo-workflows.readthedocs.io/en/latest/fields/#scripttemplate
    """

    source: str


# ----------------------------------------------------------------------------
# steps
# ----------------------------------------------------------------------------
class Step(BaseModel):
    """
    `Step`_ is a reference to a template to execute in a series of step.

    .. _Step: https://argo-workflows.readthedocs.io/en/latest/fields/#workflowstep
    """

    name: str

    arguments: Arguments | None = None
    template: str | None = None
    templateRef: TemplateRef | None = None
    when: str | None = None
    withParam: str | None = None


class TemplateRef(BaseModel):
    """
    `TemplateRef`_ is a reference of template resource.

    .. _TemplateRef: https://argo-workflows.readthedocs.io/en/latest/fields/#templateref
    """

    model_config = ConfigDict(extra="forbid")

    clusterScope: bool | None = None
    name: str
    template: str
