from __future__ import annotations

import typing

from tugboat.constraints import (
    accept_none,
    mutually_exclusive,
    require_exactly_one,
    require_all,
)
from tugboat.core import hookimpl
from tugboat.references import get_template_context
from tugboat.utils import (
    check_model_fields_references,
    check_value_references,
    find_duplicate_names,
    prepend_loc,
)

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.references import Context
    from tugboat.schemas import (
        Artifact,
        Parameter,
        Template,
        Workflow,
        WorkflowTemplate,
    )
    from tugboat.types import Diagnosis


@hookimpl(specname="analyze_template")
def check_output_parameters(
    template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    if not template.outputs:
        return

    # report duplicate names
    for idx, name in find_duplicate_names(template.outputs.parameters or ()):
        yield {
            "code": "TPL104",
            "loc": ("outputs", "parameters", idx, "name"),
            "summary": "Duplicate parameter name",
            "msg": f"Parameter name '{name}' is duplicated.",
            "input": name,
        }

    # check fields for each parameter
    context = get_template_context(workflow, template)

    for idx, param in enumerate(template.outputs.parameters or ()):
        yield from prepend_loc(
            ("outputs", "parameters", idx),
            _check_output_parameter(template, param, context),
        )


def _check_output_parameter(
    template: Template, param: Parameter, context: Context
) -> Iterable[Diagnosis]:
    yield from require_all(
        model=param,
        loc=(),
        fields=["name", "valueFrom"],
    )
    yield from accept_none(
        model=param,
        loc=(),
        fields=["value"],
    )

    if param.valueFrom:
        accept_fields = ["configMapKeyRef", "expression", "parameter"]
        match template.type:
            case "container" | "containerSet" | "script":
                accept_fields += ["path"]
            case "resource":
                accept_fields += ["jqFilter", "jsonPath"]
            case "suspend":
                accept_fields += ["supplied"]

        reject_fields = {"event", "jqFilter", "jsonPath", "path", "supplied"}
        reject_fields.difference_update(accept_fields)

        yield from require_exactly_one(
            model=param.valueFrom, loc=("valueFrom",), fields=accept_fields
        )
        yield from accept_none(
            model=param.valueFrom, loc=("valueFrom",), fields=reject_fields
        )

        # TODO check expression

    for diag in check_model_fields_references(param, context.parameters):
        match diag["code"]:
            case "VAR002":
                if metadata := diag.get("ctx", {}).get("reference"):
                    ref = metadata["found:str"]
                    diag["msg"] = (
                        f"The parameter reference '{ref}' used in parameter '{param.name}' is invalid."
                    )
        yield diag


@hookimpl(specname="analyze_template")
def check_output_artifacts(
    template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    if not template.outputs:
        return

    # report duplicate names
    for idx, name in find_duplicate_names(template.outputs.artifacts or ()):
        yield {
            "code": "TPL105",
            "loc": ("outputs", "artifacts", idx, "name"),
            "summary": "Duplicate artifact name",
            "msg": f"Artifact name '{name}' is duplicated.",
            "input": name,
        }

    # check fields for each artifact
    context = get_template_context(workflow, template)

    for idx, artifact in enumerate(template.outputs.artifacts or ()):
        yield from prepend_loc(
            ("outputs", "artifacts", idx),
            _check_output_artifact(template, artifact, context),
        )


def _check_output_artifact(
    template: Template, artifact: Artifact, context: Context
) -> Iterable[Diagnosis]:
    yield from require_all(
        model=artifact,
        loc=(),
        fields=["name"],
    )
    yield from mutually_exclusive(
        model=artifact,
        loc=(),
        fields=[
            "artifactory",
            "azure",
            "gcs",
            "hdfs",
            "http",
            "oss",
            "s3",
        ],
    )

    accept_source_fields = ["from_", "fromExpression"]
    reject_source_fields = ["git", "raw"]

    if template.type in ("container", "containerSet", "data", "script"):
        accept_source_fields.append("path")
    else:
        reject_source_fields.append("path")

    yield from require_exactly_one(model=artifact, loc=(), fields=accept_source_fields)
    yield from accept_none(model=artifact, loc=(), fields=reject_source_fields)

    if artifact.archive:
        yield from require_exactly_one(
            model=artifact.archive,
            loc=("archive",),
            fields=[
                "none",
                "tar",
                "zip",
            ],
        )

    if artifact.from_:
        for diag in prepend_loc(
            ("from",), check_value_references(artifact.from_, context.artifacts)
        ):
            match diag["code"]:
                case "VAR002":
                    if metadata := diag.get("ctx", {}).get("reference"):
                        ref = metadata["found:str"]
                        diag["msg"] = (
                            f"The artifact reference '{ref}' used in artifact '{artifact.name}' is invalid."
                        )
            yield diag

    # TODO artifact.fromExpression
