from __future__ import annotations

import itertools
import typing

from rapidfuzz.process import extractOne

from tugboat.analyzers.constraints import accept_none, require_all, require_exactly_one
from tugboat.analyzers.kubernetes import check_resource_name
from tugboat.analyzers.utils import join_with_and, prepend_loc
from tugboat.core import get_plugin_manager, hookimpl
from tugboat.schemas import Workflow, WorkflowTemplate

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.core import Diagnostic


@hookimpl
def parse_manifest(manifest: dict) -> Workflow | WorkflowTemplate | None:
    match manifest.get("kind"):
        case "Workflow":
            return Workflow.model_validate(manifest)
        case "WorkflowTemplate":
            return WorkflowTemplate.model_validate(manifest)


@hookimpl
def analyze(manifest: Workflow | WorkflowTemplate) -> Iterable[Diagnostic] | None:
    # early escape if the manifest is not recognized
    if manifest.kind not in ("Workflow", "WorkflowTemplate"):
        return None  # pragma: no cover

    # invoke checks
    pm = get_plugin_manager()

    if manifest.kind == "Workflow":
        manifest_diagnostic_iterators = pm.hook.analyze_workflow(workflow=manifest)
    else:
        manifest_diagnostic_iterators = pm.hook.analyze_workflow_template(
            workflow_template=manifest
        )
    yield from itertools.chain.from_iterable(manifest_diagnostic_iterators)

    for idx_tmpl, template in enumerate(manifest.spec.templates or []):
        template_diagnostic_iterators = pm.hook.analyze_template(
            template=template, workflow=manifest
        )
        yield from prepend_loc(
            ["spec", "templates", idx_tmpl],
            itertools.chain.from_iterable(template_diagnostic_iterators),
        )

        for idx_stage, stage in enumerate(template.steps or []):
            for idx_step, step in enumerate(stage):
                step_diagnostic_iterators = pm.hook.analyze_step(
                    step=step, template=template, workflow=manifest
                )
                yield from prepend_loc(
                    ["spec", "templates", idx_tmpl, "steps", idx_stage, idx_step],
                    itertools.chain.from_iterable(step_diagnostic_iterators),
                )


# ----------------------------------------------------------------------------
# Workflow analyzers
# ----------------------------------------------------------------------------


@hookimpl(specname="analyze_workflow")
def check_metadata(workflow: Workflow) -> Iterable[Diagnostic]:
    yield from require_exactly_one(
        model=workflow.metadata,
        loc=("metadata",),
        fields=["name", "generateName"],
    )

    if workflow.metadata.name:
        if diagnostic := check_resource_name(workflow.metadata.name):
            diagnostic["loc"] = ("metadata", "name")
            yield diagnostic

    if workflow.metadata.generateName:
        if diagnostic := check_resource_name(
            workflow.metadata.generateName, is_generate_name=True
        ):
            diagnostic["loc"] = ("metadata", "generateName")
            yield diagnostic


@hookimpl(specname="analyze_workflow")
def check_spec(workflow: Workflow) -> Iterable[Diagnostic]:
    yield from require_exactly_one(
        model=workflow.spec,
        loc=("spec",),
        fields=["templates", "workflowTemplateRef"],
    )

    if not workflow.spec.workflowTemplateRef:
        yield from require_all(
            model=workflow.spec,
            loc=("spec",),
            fields=["entrypoint"],
        )


@hookimpl(specname="analyze_workflow")
def check_entrypoint(workflow: Workflow | WorkflowTemplate) -> Iterable[Diagnostic]:
    if not workflow.spec.templates:
        return

    # count the number of times each name appears
    entrypoints = {}
    for idx, template in enumerate(workflow.spec.templates or []):
        loc = ("spec", "templates", idx)
        # ensure that the template has a name
        yield from require_all(model=template, loc=loc, fields=["name"])
        # if the template has a name, add it to the entrypoints
        if template.name:
            entrypoints.setdefault(template.name, []).append(loc)

    # if the spec has an entrypoint, check that it exists
    if workflow.spec.entrypoint and workflow.spec.entrypoint not in entrypoints:
        suggestion, _, _ = extractOne(workflow.spec.entrypoint, entrypoints)
        entrypoints_ = sorted(entrypoints)
        yield {
            "code": "WF001",
            "loc": ("spec", "entrypoint"),
            "summary": "Invalid entrypoint",
            "msg": f"""
                Entrypoint '{workflow.spec.entrypoint}' is not defined in any template.
                Defined entrypoints: {join_with_and(entrypoints_)}.
                """,
            "input": workflow.spec.entrypoint,
            "fix": suggestion,
        }

    # report duplicates
    for name, locs in entrypoints.items():
        if len(locs) > 1:
            for loc in locs:
                yield {
                    "code": "WF002",
                    "loc": loc,
                    "summary": "Duplicated template name",
                    "msg": f"Template name '{name}' is duplicated.",
                    "input": name,
                }


@hookimpl(specname="analyze_workflow")
def check_argument_parameters(
    workflow: Workflow | WorkflowTemplate,
) -> Iterable[Diagnostic]:
    if not workflow.spec.arguments:
        return

    # check fields for each parameter; also count the number of times each name appears
    parameters = {}
    for idx, param in enumerate(workflow.spec.arguments.parameters or []):
        loc = ("spec", "arguments", "parameters", idx)

        yield from require_all(
            model=param,
            loc=loc,
            fields=["name"],
        )
        yield from require_exactly_one(
            model=param,
            loc=loc,
            fields=["value", "valueFrom"],
        )
        yield from accept_none(
            model=param,
            loc=loc,
            fields=["default", "enum"],
        )

        if param.name:
            parameters.setdefault(param.name, []).append(loc)

        if param.valueFrom:
            yield from require_exactly_one(
                model=param.valueFrom,
                loc=(*loc, "valueFrom"),
                fields=[
                    "configMapKeyRef",
                    "expression",
                ],
            )
            yield from accept_none(
                model=param.valueFrom,
                loc=(*loc, "valueFrom"),
                fields=[
                    "default",
                    "event",
                    "jqFilter",
                    "jsonPath",
                    "parameter",
                    "path",
                    "supplied",
                ],
            )

    # report duplicates
    for name, locs in parameters.items():
        if len(locs) > 1:
            for loc in locs:
                yield {
                    "code": "WF003",
                    "loc": loc,
                    "summary": "Duplicated parameter name",
                    "msg": f"Parameter name '{name}' is duplicated.",
                    "input": name,
                }


@hookimpl(specname="analyze_workflow")
def check_argument_artifacts(
    workflow: Workflow | WorkflowTemplate,
) -> Iterable[Diagnostic]:
    if not workflow.spec.arguments:
        return

    # check fields for each artifact; also count the number of times each name appears
    artifacts = {}
    for idx, artifact in enumerate(workflow.spec.arguments.artifacts or []):
        loc = ("spec", "arguments", "artifacts", idx)

        yield from require_exactly_one(
            model=artifact,
            loc=loc,
            fields=[
                "artifactory",
                "azure",
                "gcs",
                "git",
                "hdfs",
                "http",
                "oss",
                "raw",
                "s3",
            ],
        )
        yield from accept_none(
            model=artifact,
            loc=loc,
            fields=[
                "archive",
                "archiveLogs",
                "artifactGC",
                "deleted",
                "from_",
                "fromExpression",
                "mode",
                "path",
                "recurseMode",
            ],
        )

        if artifact.name:
            artifacts.setdefault(artifact.name, []).append(loc)

    # report duplicates
    for name, locs in artifacts.items():
        if len(locs) > 1:
            for loc in locs:
                yield {
                    "code": "WF004",
                    "loc": loc,
                    "summary": "Duplicated artifact name",
                    "msg": f"Artifact name '{name}' is duplicated.",
                    "input": name,
                }