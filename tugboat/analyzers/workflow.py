from __future__ import annotations

import itertools
import typing

from rapidfuzz.process import extractOne

from tugboat.analyzers.kubernetes import check_resource_name
from tugboat.constraints import accept_none, require_exactly_one, require_non_empty
from tugboat.core import get_plugin_manager, hookimpl
from tugboat.utils import find_duplicate_names, join_with_and, prepend_loc

if typing.TYPE_CHECKING:
    from collections.abc import Iterator

    from tugboat.schemas import Workflow, WorkflowTemplate
    from tugboat.types import Diagnosis

    type WorkflowCompatible = Workflow | WorkflowTemplate


@hookimpl
def analyze(manifest: WorkflowCompatible) -> Iterator[Diagnosis]:
    # early escape if the manifest is not recognized
    if manifest.apiVersion != "argoproj.io/v1alpha1":
        return
    if manifest.kind not in ("Workflow", "WorkflowTemplate"):
        return

    # invoke checks
    pm = get_plugin_manager()

    if manifest.kind == "Workflow":
        manifest_diagnoses_generators = pm.hook.analyze_workflow(workflow=manifest)
    else:
        manifest_diagnoses_generators = pm.hook.analyze_workflow_template(
            workflow_template=manifest
        )
    yield from itertools.chain.from_iterable(manifest_diagnoses_generators)

    for idx_tmpl, template in enumerate(manifest.spec.templates or []):
        template_diagnoses_generators = pm.hook.analyze_template(
            template=template, workflow=manifest
        )
        yield from prepend_loc(
            ["spec", "templates", idx_tmpl],
            itertools.chain.from_iterable(template_diagnoses_generators),
        )

        for idx_stage, stage in enumerate(template.steps or []):
            for idx_step, step in enumerate(stage):
                step_diagnoses_generators = pm.hook.analyze_step(
                    step=step, template=template, workflow=manifest
                )
                yield from prepend_loc(
                    ["spec", "templates", idx_tmpl, "steps", idx_stage, idx_step],
                    itertools.chain.from_iterable(step_diagnoses_generators),
                )


# ----------------------------------------------------------------------------
# Workflow analyzers
# ----------------------------------------------------------------------------


@hookimpl(specname="analyze_workflow")
def check_metadata(workflow: Workflow) -> Iterator[Diagnosis]:
    yield from require_exactly_one(
        model=workflow.metadata,
        loc=("metadata",),
        fields=["name", "generateName"],
    )

    if workflow.metadata.name:
        yield from prepend_loc(
            ["metadata", "name"], check_resource_name(workflow.metadata.name)
        )

    if workflow.metadata.generateName:
        yield from prepend_loc(
            ["metadata", "generateName"],
            check_resource_name(workflow.metadata.generateName, is_generate_name=True),
        )


@hookimpl(specname="analyze_workflow")
def check_spec(workflow: Workflow) -> Iterator[Diagnosis]:
    yield from require_exactly_one(
        model=workflow.spec,
        loc=("spec",),
        fields=["templates", "workflowTemplateRef"],
    )

    if not workflow.spec.workflowTemplateRef:
        yield from require_non_empty(
            model=workflow.spec,
            loc=("spec",),
            fields=["entrypoint"],
        )


@hookimpl(specname="analyze_workflow")
def check_entrypoint(workflow: WorkflowCompatible) -> Iterator[Diagnosis]:
    if not workflow.spec.templates:
        return

    # report duplicate names
    for idx, name in find_duplicate_names(workflow.spec.templates):
        yield {
            "code": "TPL001",
            "loc": ("spec", "templates", idx, "name"),
            "summary": "Duplicate template name",
            "msg": f"Template name '{name}' is duplicated.",
            "input": name,
        }

    # if the workflow has an entrypoint, check if it exists
    if (
        True
        and workflow.spec.entrypoint
        and workflow.spec.entrypoint not in workflow.template_dict
    ):
        entrypoints = sorted(workflow.template_dict)
        suggestion = None
        if result := extractOne(workflow.spec.entrypoint, entrypoints):
            suggestion, _, _ = result
        yield {
            "code": "WF001",
            "loc": ("spec", "entrypoint"),
            "summary": "Invalid entrypoint",
            "msg": f"""
                Entrypoint '{workflow.spec.entrypoint}' is not defined in any template.
                Defined entrypoints: {join_with_and(entrypoints)}
                """,
            "input": workflow.spec.entrypoint,
            "fix": suggestion,
        }


@hookimpl(specname="analyze_workflow")
def check_argument_parameters(workflow: WorkflowCompatible) -> Iterator[Diagnosis]:
    if not workflow.spec.arguments:
        return

    # report duplicate names
    for idx, name in find_duplicate_names(workflow.spec.arguments.parameters or ()):
        yield {
            "code": "WF002",
            "loc": ("spec", "arguments", "parameters", idx, "name"),
            "summary": "Duplicate parameter name",
            "msg": f"Parameter name '{name}' is duplicated.",
            "input": name,
        }

    # check fields for each parameter
    for idx, param in enumerate(workflow.spec.arguments.parameters or []):
        loc = ("spec", "arguments", "parameters", idx)

        yield from require_non_empty(
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


@hookimpl(specname="analyze_workflow")
def check_argument_artifacts(workflow: WorkflowCompatible) -> Iterator[Diagnosis]:
    if not workflow.spec.arguments:
        return

    # report duplicate names
    for idx, name in find_duplicate_names(workflow.spec.arguments.artifacts or ()):
        yield {
            "code": "WF003",
            "loc": ("spec", "arguments", "artifacts", idx, "name"),
            "summary": "Duplicate artifact name",
            "msg": f"Artifact name '{name}' is duplicated.",
            "input": name,
        }

    # check fields for each artifact; also count the number of times each name appears
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
