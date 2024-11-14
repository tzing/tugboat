from __future__ import annotations

import typing

from tugboat.hookspecs.core import hookspec

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.core import Diagnosis
    from tugboat.schemas import Step, Template, Workflow, WorkflowTemplate


@hookspec
def analyze_workflow(workflow: Workflow) -> Iterable[Diagnosis]:  # type: ignore[reportReturnType]
    """
    Analyze a workflow.

    Parameters
    ----------
    workflow : Workflow
        The workflow to analyze.
    """


@hookspec
def analyze_workflow_template(workflow_template: WorkflowTemplate) -> Iterable[Diagnosis]:  # type: ignore[reportReturnType]
    """
    Analyze a workflow template.

    Parameters
    ----------
    workflow_template : WorkflowTemplate
        The workflow template to analyze.
    """


@hookspec
def analyze_template(template: Template, workflow: Workflow | WorkflowTemplate) -> Iterable[Diagnosis]:  # type: ignore[reportReturnType]
    """
    Analyze a template.

    This hook is called for each template in a workflow or workflow template, but not including the 'templateDefaults'.

    Parameters
    ----------
    template : Template
        The template to analyze.
    workflow : Workflow | WorkflowTemplate
        The workflow that the template is part of.
    """


@hookspec
def analyze_step(
    step: Step, template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:  # type: ignore[reportReturnType]
    """
    Analyze a workflow step.

    Parameters
    ----------
    step : Step
        The step to analyze.
    template : Template
        The template that the step is part of.
    workflow : Workflow | WorkflowTemplate
        The workflow that the template is part of.
    """
