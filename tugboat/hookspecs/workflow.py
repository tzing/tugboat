from __future__ import annotations

import typing

from tugboat.hookspecs.core import hookspec

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.core import Diagnostic
    from tugboat.schemas import Step, Template, Workflow, WorkflowTemplate


@hookspec
def analyze_workflow(workflow: Workflow | WorkflowTemplate) -> Iterable[Diagnostic]:  # type: ignore[reportReturnType]
    """
    Analyze a workflow or a workflow template.

    Parameters
    ----------
    workflow : Workflow | WorkflowTemplate
        The workflow to analyze.
    """


@hookspec
def analyze_template(template: Template, workflow: Workflow | WorkflowTemplate) -> Iterable[Diagnostic]:  # type: ignore[reportReturnType]
    """
    Analyze a template.

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
) -> Iterable[Diagnostic]:  # type: ignore[reportReturnType]
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
