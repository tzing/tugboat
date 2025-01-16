from __future__ import annotations

import re
import typing

from tugboat.analyzers.generic import (
    check_model_fields_references,
    check_value_references,
    report_duplicate_names,
)
from tugboat.constraints import (
    accept_none,
    mutually_exclusive,
    require_all,
    require_exactly_one,
)
from tugboat.core import hookimpl
from tugboat.references import get_step_context
from tugboat.utils import prepend_loc

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.references import Context
    from tugboat.schemas import (
        Artifact,
        Parameter,
        Step,
        Template,
        Workflow,
        WorkflowTemplate,
    )
    from tugboat.types import Diagnosis


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


def check_input_parameter(param: Parameter, context: Context) -> Iterable[Diagnosis]:
    yield from require_all(
        model=param,
        loc=(),
        fields=["name"],
    )
    yield from mutually_exclusive(
        model=param,
        loc=(),
        fields=["value", "valueFrom"],
    )

    if param.valueFrom:
        yield from require_exactly_one(
            model=param.valueFrom,
            loc=("valueFrom",),
            fields=[
                "configMapKeyRef",
                "expression",
                "parameter",
            ],
        )
        yield from accept_none(
            model=param.valueFrom,
            loc=("valueFrom",),
            fields=[
                "event",
                "globalName",
                "jqFilter",
                "jsonPath",
                "path",
                "supplied",
            ],
        )

    for diag in check_model_fields_references(param, context.parameters):
        match diag["code"]:
            case "VAR002":
                ctx = typing.cast(dict, diag.get("ctx"))
                ref = ".".join(ctx["ref"])
                diag["msg"] = (
                    f"The parameter reference '{ref}' used in parameter '{param.name}' is invalid."
                )
        yield diag


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


def check_input_artifact(artifact: Artifact, context: Context) -> Iterable[Diagnosis]:
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
            "from_",
            "fromExpression",
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
        loc=(),
        fields=[
            "archive",
            "archiveLogs",
            "artifactGC",
            "deleted",
            "globalName",
        ],
    )

    if artifact.from_:
        # `from` value can be either wrapped by the cruely brackets or not

        # when it is unwrapped, it is a reference to an artifact
        # EXAMPLE> artifact: inputs.artifacts.artifact-1
        if re.fullmatch(r"\s*[a-zA-Z0-9.-]+\s*", artifact.from_):
            ref = tuple(artifact.from_.strip().split("."))
            closest = context.artifacts.find_closest(ref)
            if ref not in context.artifacts:
                yield {
                    "code": "VAR002",
                    "loc": ("from",),
                    "summary": "Invalid reference",
                    "msg": f"The reference '{artifact.from_}' used in artifact '{artifact.name}' is invalid.",
                    "input": artifact.from_,
                    "fix": ".".join(closest),
                }

        # when it is wrapped, it may be a reference to a parameter or an artifact
        mixed_references = context.parameters + context.artifacts
        for diag in prepend_loc(
            ("from",), check_value_references(artifact.from_, mixed_references)
        ):
            match diag["code"]:
                case "VAR002":
                    ctx = typing.cast(dict, diag.get("ctx"))
                    ref = ".".join(ctx["ref"])
                    diag["msg"] = (
                        f"The reference '{ref}' used in artifact '{artifact.name}' is invalid."
                    )
            yield diag

    # TODO fromExpression

    if artifact.raw:
        for diag in prepend_loc(
            ("raw", "data"),
            check_value_references(artifact.raw.data, context.parameters),
        ):
            match diag["code"]:
                case "VAR002":
                    ctx = typing.cast(dict, diag.get("ctx"))
                    ref = ".".join(ctx["ref"])
                    diag["msg"] = (
                        f"""
                        The parameter reference '{ref}' used in artifact '{artifact.name}' is invalid.
                        Note: Only parameter references are allowed here, even though this is an artifact object.
                        """
                    )
            yield diag
