from __future__ import annotations

import itertools
import typing

import tugboat.analyzers.workflow
from tugboat.analyzers.kubernetes import check_resource_name
from tugboat.constraints import require_exactly_one
from tugboat.core import hookimpl
from tugboat.utils import prepend_loc

if typing.TYPE_CHECKING:
    from collections.abc import Iterator

    from tugboat.schemas import WorkflowTemplate
    from tugboat.types import Diagnosis


@hookimpl(specname="analyze_workflow_template")
def check_metadata(workflow_template: WorkflowTemplate) -> Iterator[Diagnosis]:
    yield from require_exactly_one(
        model=workflow_template.metadata,
        loc=("metadata",),
        fields=["name", "generateName"],
    )

    if workflow_template.metadata.name:
        yield from prepend_loc(
            ["metadata", "name"],
            check_resource_name(workflow_template.metadata.name, max_length=63),
        )

    if workflow_template.metadata.generateName:
        yield {
            "code": "WT004",
            "loc": ("metadata", "generateName"),
            "summary": "Use strict name",
            "msg": "Use a strict name instead of a generateName.",
            "input": "generateName",
            "fix": "name",
        }


@hookimpl(specname="analyze_workflow_template")
def check_spec(workflow_template: WorkflowTemplate) -> Iterator[Diagnosis]:
    yield from require_exactly_one(
        model=workflow_template.spec,
        loc=("spec",),
        fields=["templates", "workflowTemplateRef"],
    )


@hookimpl(specname="analyze_workflow_template")
def check_entrypoint(workflow_template: WorkflowTemplate) -> Iterator[Diagnosis]:
    for diagnosis in tugboat.analyzers.workflow.check_entrypoint(workflow_template):
        match diagnosis["code"]:
            case "WF001":
                diagnosis["code"] = "WT001"
        yield diagnosis


@hookimpl(specname="analyze_workflow_template")
def check_arguments(workflow_template: WorkflowTemplate) -> Iterator[Diagnosis]:
    for diagnosis in itertools.chain(
        tugboat.analyzers.workflow.check_argument_parameters(workflow_template),
        tugboat.analyzers.workflow.check_argument_artifacts(workflow_template),
    ):
        match diagnosis["code"]:
            case "WF002":
                diagnosis["code"] = "WT002"
            case "WF003":
                diagnosis["code"] = "WT003"
        yield diagnosis
