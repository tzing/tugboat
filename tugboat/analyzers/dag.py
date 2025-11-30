from __future__ import annotations

import logging
import typing

from rapidfuzz.process import extractOne

import tugboat.analyzers.step as step_analyzer
from tugboat.constraints import mutually_exclusive
from tugboat.core import hookimpl
from tugboat.references import get_task_context
from tugboat.types import Field
from tugboat.utils import (
    find_duplicate_names,
    join_with_or,
    prepend_loc,
)

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.schemas import DagTask, Template, Workflow, WorkflowTemplate
    from tugboat.types import Diagnosis

    type WorkflowCompatible = Workflow | WorkflowTemplate

logger = logging.getLogger(__name__)


@hookimpl
def analyze_task(
    task: DagTask, template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    yield from mutually_exclusive(
        task,
        fields=["template", "templateRef", "inline"],
        require_one=True,
    )
    yield from mutually_exclusive(
        task,
        fields=["withItems", "withParam", "withSequence"],
    )
    yield from mutually_exclusive(
        task,
        fields=["depends", "dependencies"],
    )

    if task.onExit:
        yield {
            "type": "warning",
            "code": "DAG901",
            "loc": ("onExit",),
            "summary": "Deprecated field",
            "msg": "Field 'onExit' is deprecated. Please use 'hooks[exit].template' instead.",
            "input": Field("onExit"),
        }


@hookimpl(specname="analyze_task")
def check_argument_parameters(
    task: DagTask, template: Template, workflow: WorkflowCompatible
) -> Iterable[Diagnosis]:
    if not task.arguments:
        return
    if not task.arguments.parameters:
        return

    # report duplicate names
    for idx, name in find_duplicate_names(task.arguments.parameters):
        yield {
            "code": "DAG102",
            "loc": ("arguments", "parameters", idx, "name"),
            "summary": "Duplicate parameter name",
            "msg": f"Parameter name '{name}' is duplicated.",
            "input": name,
        }

    # check fields for each parameter
    ctx = get_task_context(workflow, template, task)

    for idx, param in enumerate(task.arguments.parameters):
        for diag in step_analyzer.check_argument_parameter_fields(param, ctx):
            diag["loc"] = ["arguments", "parameters", idx, *diag["loc"]]

            match diag["code"]:
                case "STP301":
                    diag["code"] = "DAG301"
            yield diag


@hookimpl(specname="analyze_task")
def check_argument_artifacts(
    task: DagTask, template: Template, workflow: WorkflowCompatible
) -> Iterable[Diagnosis]:
    if not task.arguments:
        return
    if not task.arguments.artifacts:
        return

    # report duplicate names
    for idx, name in find_duplicate_names(task.arguments.artifacts):
        yield {
            "code": "DAG103",
            "loc": ("arguments", "artifacts", idx, "name"),
            "summary": "Duplicate artifact name",
            "msg": f"Artifact name '{name}' is duplicated.",
            "input": name,
        }

    # check fields for each parameter
    ctx = get_task_context(workflow, template, task)

    for idx, artifact in enumerate(task.arguments.artifacts):
        for diag in step_analyzer.check_argument_artifact_fields(artifact, ctx):
            diag["loc"] = ["arguments", "artifacts", idx, *diag["loc"]]

            match diag["code"]:
                case "STP302":
                    diag["code"] = "DAG302"
                case "STP303":
                    diag["code"] = "DAG303"
            yield diag


@hookimpl(specname="analyze_task")
def check_argument_parameters_usage(
    task: DagTask, workflow: WorkflowCompatible
) -> Iterable[Diagnosis]:
    for diag in step_analyzer.check_argument_parameters_usage(task, workflow):
        match diag["code"]:
            case "STP304":
                diag["code"] = "DAG304"
            case "STP305":
                diag["code"] = "DAG305"
        yield diag


@hookimpl(specname="analyze_task")
def check_referenced_template(
    task: DagTask, template: Template, workflow: WorkflowCompatible
) -> Iterable[Diagnosis]:
    if task.template:
        yield from prepend_loc(
            ("template",),
            _check_referenced_template(task.template, template, workflow),
        )

    elif task.templateRef:
        if task.templateRef.name == workflow.metadata.name:
            yield from prepend_loc(
                ("templateRef", "template"),
                _check_referenced_template(
                    task.templateRef.template, template, workflow
                ),
            )
        else:
            logger.debug(
                "Task '%s': Referenced template '%s' is not the same as current workflow '%s'. Skipping.",
                task.name,
                task.templateRef.name,
                workflow.name,
            )


def _check_referenced_template(
    target_template_name: str, template: Template, workflow: WorkflowCompatible
) -> Iterable[Diagnosis]:
    if target_template_name == template.name:
        yield {
            "type": "warning",
            "code": "DAG201",
            "loc": (),
            "summary": "Self-referencing",
            "msg": "Self-referencing may cause infinite recursion.",
            "input": target_template_name,
        }

    if target_template_name not in workflow.template_dict:
        templates = set(workflow.template_dict)
        templates -= {template.name}

        suggestion = None
        if result := extractOne(target_template_name, templates):
            suggestion, _, _ = result

        yield {
            "code": "DAG202",
            "loc": (),
            "summary": "Template not found",
            "msg": (
                f"""
                Template '{target_template_name}' does not exist in the workflow.
                Available templates: {join_with_or(templates)}
                """
            ),
            "input": target_template_name,
            "fix": suggestion,
        }
