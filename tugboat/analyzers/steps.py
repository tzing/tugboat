from __future__ import annotations

import typing

from tugboat.analyzers.generic import report_duplicate_names
from tugboat.analyzers.template import check_input_artifact, check_input_parameter
from tugboat.core import hookimpl
from tugboat.references import get_step_context
from tugboat.utils import prepend_loc

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.core import Diagnosis
    from tugboat.schemas import Step, Template, Workflow, WorkflowTemplate

    type DocumentMap = dict[tuple[str | int, ...], str]


@hookimpl(specname="analyze_step")
def check_argument_parameters(
    step: Step, template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    if not step.arguments:
        return

    # report duplicate names
    for idx, name in report_duplicate_names(step.arguments.parameters or ()):
        yield {
            "code": "STP002",
            "loc": ("arguments", "parameters", idx, "name"),
            "summary": "Duplicate parameter name",
            "msg": f"Parameter name '{name}' is duplicated.",
            "input": name,
        }

    # check fields for each parameter
    ctx = get_step_context(workflow, template, step)

    for idx, param in enumerate(step.arguments.parameters or ()):
        yield from prepend_loc(
            ("arguments", "parameters", idx), check_input_parameter(param, ctx)
        )


@hookimpl(specname="analyze_step")
def check_argument_artifacts(
    step: Step, template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    if not step.arguments:
        return

    # report duplicate names
    for idx, name in report_duplicate_names(step.arguments.artifacts or ()):
        yield {
            "code": "STP003",
            "loc": ("arguments", "artifacts", idx, "name"),
            "summary": "Duplicate artifact name",
            "msg": f"Artifact name '{name}' is duplicated.",
            "input": name,
        }

    # check fields for each parameter
    ctx = get_step_context(workflow, template, step)

    for idx, artifact in enumerate(step.arguments.artifacts or []):
        yield from prepend_loc(
            ("arguments", "artifacts", idx), check_input_artifact(artifact, ctx)
        )
