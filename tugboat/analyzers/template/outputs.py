from __future__ import annotations

import typing

from tugboat.constraints import (
    accept_none,
    mutually_exclusive,
    require_exactly_one,
    require_non_empty,
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
            "code": "TPL004",
            "loc": ("outputs", "parameters", idx, "name"),
            "summary": "Duplicate parameter name",
            "msg": f"Parameter name '{name}' is duplicated.",
            "input": name,
        }

    # check fields for each parameter
    context = get_template_context(workflow, template)

    for idx, param in enumerate(template.outputs.parameters or ()):
        yield from prepend_loc(
            ("outputs", "parameters", idx), _check_output_parameter(param, context)
        )


def _check_output_parameter(param: Parameter, context: Context) -> Iterable[Diagnosis]:
    yield from require_non_empty(
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
        yield from require_exactly_one(
            model=param.valueFrom,
            loc=("valueFrom",),
            fields=[
                "configMapKeyRef",
                "event",
                "expression",
                "jqFilter",
                "jsonPath",
                "parameter",
                "path",
                "supplied",
            ],
        )

        # TODO check expression

    for diag in check_model_fields_references(param, context.parameters):
        match diag["code"]:
            case "VAR002":
                ctx = typing.cast(dict, diag.get("ctx"))
                ref = ".".join(ctx["ref"])
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
            "code": "TPL005",
            "loc": ("outputs", "artifacts", idx, "name"),
            "summary": "Duplicate artifact name",
            "msg": f"Artifact name '{name}' is duplicated.",
            "input": name,
        }

    # check fields for each artifact
    context = get_template_context(workflow, template)

    for idx, artifact in enumerate(template.outputs.artifacts or ()):
        yield from prepend_loc(
            ("outputs", "artifacts", idx), _check_output_artifact(artifact, context)
        )


def _check_output_artifact(artifact: Artifact, context: Context) -> Iterable[Diagnosis]:
    yield from require_non_empty(
        model=artifact,
        loc=(),
        fields=["name"],
    )
    yield from require_exactly_one(
        model=artifact,
        loc=(),
        fields=[
            "from_",
            "fromExpression",
            "path",
        ],
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
    yield from accept_none(
        model=artifact,
        loc=(),
        fields=[
            "git",
            "raw",
        ],
    )

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
                    ctx = typing.cast(dict, diag.get("ctx"))
                    ref = ".".join(ctx["ref"])
                    diag["msg"] = (
                        f"The artifact reference '{ref}' used in artifact '{artifact.name}' is invalid."
                    )
            yield diag

    # TODO artifact.fromExpression
