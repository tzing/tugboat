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
def check_manifest(workflow: Workflow):
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

    yield from require_exactly_one(
        model=workflow.spec,
        loc=("spec",),
        fields=["templates", "workflowTemplateRef"],
    )


@hookimpl(specname="analyze_workflow")
def check_entrypoint(workflow: Workflow):
    if workflow.spec.workflowTemplateRef:
        return
    yield from require_all(
        model=workflow.spec,
        loc=("spec",),
        fields=["entrypoint"],
    )


@hookimpl(specname="analyze_workflow")
def check_entrypoint_exists(workflow: Workflow):
    if workflow.spec.entrypoint is None:
        return
    if not workflow.spec.templates:
        return

    entrypoints = {template.name for template in workflow.spec.templates}

    if workflow.spec.entrypoint not in entrypoints:
        suggestion, _, _ = extractOne(workflow.spec.entrypoint, entrypoints)
        entrypoints = sorted(filter(None, entrypoints))
        yield {
            "code": "WF001",
            "loc": ("spec", "entrypoint"),
            "summary": "Invalid entrypoint",
            "msg": f"""
                Entrypoint '{workflow.spec.entrypoint}' is not defined in any template.
                Defined entrypoints: {join_with_and(entrypoints)}.
                """,
            "input": workflow.spec.entrypoint,
            "fix": suggestion,
        }


@hookimpl(specname="analyze_workflow")
def check_workflow_argument_parameters(workflow: Workflow):
    if not workflow.spec.arguments:
        return

    for idx, param in enumerate(workflow.spec.arguments.parameters or []):
        loc = ("spec", "arguments", "parameters", idx)

        yield from accept_none(
            model=param,
            loc=loc,
            fields=["default", "enum"],
        )
        yield from require_exactly_one(
            model=param,
            loc=loc,
            fields=["value", "valueFrom"],
        )

        if param.valueFrom:
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
            yield from require_exactly_one(
                model=param.valueFrom,
                loc=(*loc, "valueFrom"),
                fields=[
                    "configMapKeyRef",
                    "expression",
                ],
            )


@hookimpl(specname="analyze_workflow")
def check_workflow_argument_parameter_names(workflow: Workflow):
    if not workflow.spec.arguments:
        return

    # count the number of times each name appears
    counter = {}
    for idx, param in enumerate(workflow.spec.arguments.parameters or []):
        loc = ("spec", "arguments", "parameters", idx)
        yield from require_all(model=param, loc=loc, fields=["name"])
        if param.name:
            counter.setdefault(param.name, []).append(loc)

    # report duplicates
    for name, locs in counter.items():
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
def check_workflow_argument_artifacts(workflow: Workflow):
    if not workflow.spec.arguments:
        return

    for idx, artifact in enumerate(workflow.spec.arguments.artifacts or []):
        loc = ("spec", "arguments", "artifacts", idx)

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


@hookimpl(specname="analyze_workflow")
def check_workflow_argument_artifact_names(workflow: Workflow):
    if not workflow.spec.arguments:
        return

    # count the number of times each name appears
    counter = {}
    for idx, artifact in enumerate(workflow.spec.arguments.artifacts or []):
        loc = ("spec", "arguments", "artifacts", idx)
        yield from require_all(model=artifact, loc=loc, fields=["name"])
        if artifact.name:
            counter.setdefault(artifact.name, []).append(loc)

    # report duplicates
    for name, locs in counter.items():
        if len(locs) > 1:
            for loc in locs:
                yield {
                    "code": "WF004",
                    "loc": loc,
                    "summary": "Duplicated artifact name",
                    "msg": f"Artifact name '{name}' is duplicated.",
                    "input": name,
                }


@hookimpl(specname="analyze_workflow")
def check_template_names(workflow: Workflow):
    # count the number of times each name appears
    counter = {}
    for idx, template in enumerate(workflow.spec.templates or []):
        loc = ("spec", "templates", idx)
        yield from require_all(model=template, loc=loc, fields=["name"])
        if template.name:
            counter.setdefault(template.name, []).append(loc)

    # report duplicates
    for name, locs in counter.items():
        if len(locs) > 1:
            for loc in locs:
                yield {
                    "code": "WF002",
                    "loc": loc,
                    "summary": "Duplicated template name",
                    "msg": f"Template name '{name}' is duplicated.",
                    "input": name,
                }
