from __future__ import annotations

import itertools
import typing

import tugboat.analyzers.workflow
from tugboat.analyzers.constraints import require_exactly_one
from tugboat.analyzers.kubernetes import check_resource_name
from tugboat.core import hookimpl

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.core import Diagnostic
    from tugboat.schemas import WorkflowTemplate


@hookimpl(specname="analyze_workflow_template")
def check_metadata(workflow_template: WorkflowTemplate) -> Iterable[Diagnostic]:
    yield from require_exactly_one(
        model=workflow_template.metadata,
        loc=("metadata",),
        fields=["name", "generateName"],
    )

    if workflow_template.metadata.name:
        if diagnostic := check_resource_name(
            workflow_template.metadata.name, length=63
        ):
            diagnostic["loc"] = ("metadata", "name")
            yield diagnostic

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
def check_spec(workflow_template: WorkflowTemplate) -> Iterable[Diagnostic]:
    yield from require_exactly_one(
        model=workflow_template.spec,
        loc=("spec",),
        fields=["templates", "workflowTemplateRef"],
    )


@hookimpl(specname="analyze_workflow_template")
def check_entrypoint(workflow_template: WorkflowTemplate) -> Iterable[Diagnostic]:
    for diagnostic in tugboat.analyzers.workflow.check_entrypoint(workflow_template):
        match diagnostic["code"]:
            case "WF001":
                diagnostic["code"] = "WT001"
        yield diagnostic


@hookimpl(specname="analyze_workflow_template")
def check_arguments(
    workflow_template: WorkflowTemplate,
) -> Iterable[Diagnostic]:
    for diagnostic in itertools.chain(
        tugboat.analyzers.workflow.check_argument_parameters(workflow_template),
        tugboat.analyzers.workflow.check_argument_artifacts(workflow_template),
    ):
        match diagnostic["code"]:
            case "WT002":
                diagnostic["code"] = "WT002"
            case "WT003":
                diagnostic["code"] = "WT003"
        yield diagnostic
