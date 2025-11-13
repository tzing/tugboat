from __future__ import annotations

import typing

from tugboat.constraints import (
    accept_none,
    mutually_exclusive,
    require_all,
    require_all,
)
from tugboat.core import hookimpl
from tugboat.references import get_workflow_context
from tugboat.types import Field
from tugboat.utils import (
    check_model_fields_references,
    check_value_references,
    find_duplicate_names,
    prepend_loc,
)

if typing.TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Literal

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
def check_input_parameters(
    template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    if not template.inputs:
        return

    # report duplicate names
    for idx, name in find_duplicate_names(template.inputs.parameters or ()):
        yield {
            "code": "TPL102",
            "loc": ("inputs", "parameters", idx, "name"),
            "summary": "Duplicate parameter name",
            "msg": f"Parameter name '{name}' is duplicated.",
            "input": name,
        }

    # check fields for each parameter
    ctx = get_workflow_context(workflow)

    for idx, param in enumerate(template.inputs.parameters or ()):
        yield from prepend_loc(
            ("inputs", "parameters", idx),
            _check_input_parameter(workflow.kind, param, ctx),
        )


def _check_input_parameter(
    kind: Literal["Workflow", "WorkflowTemplate"],
    param: Parameter,
    context: Context,
) -> Iterable[Diagnosis]:
    # generic checks for all parameters
    yield from require_all(
        model=param,
        loc=(),
        fields=["name"],
    )
    yield from accept_none(
        model=param,
        loc=(),
        fields=["globalName"],
    )

    for diag in check_model_fields_references(param, context.parameters):
        match diag["code"]:
            case "VAR002":
                diag["code"] = "TPL201"
                if metadata := diag.get("ctx", {}).get("reference"):
                    ref = metadata["found:str"]
                    diag["msg"] = (
                        f"The parameter reference '{ref}' used in parameter '{param.name}' is invalid."
                    )
        yield diag

    # kind-specific checks
    if kind == "Workflow":
        yield from mutually_exclusive(
            model=param,
            loc=(),
            fields=["value", "valueFrom"],
        )

    elif kind == "WorkflowTemplate":
        yield from mutually_exclusive(
            model=param,
            loc=(),
            fields=["value", "valueFrom", "default"],
        )

        if param.value:
            yield {
                "type": "failure",
                "code": "M102",
                "loc": ("value",),
                "summary": "Found redundant field 'value'",
                "msg": (
                    """
                    The 'value' field in a WorkflowTemplate input parameter may cause issues.
                    Use 'default' instead to set a default value for the parameter.
                    """
                ),
                "input": Field("value"),
                "fix": "default",
            }

    # field-specific checks
    if param.valueFrom:
        yield from require_all(
            model=param.valueFrom,
            loc=("valueFrom",),
            fields=["configMapKeyRef"],
        )
        yield from accept_none(
            model=param.valueFrom,
            loc=("valueFrom",),
            fields=[
                "event",
                "expression",
                "jqFilter",
                "jsonPath",
                "parameter",
                "path",
                "supplied",
            ],
        )


@hookimpl(specname="analyze_template")
def check_input_artifacts(
    template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    if not template.inputs:
        return

    # report duplicate names
    for idx, name in find_duplicate_names(template.inputs.artifacts or ()):
        yield {
            "code": "TPL103",
            "loc": ("inputs", "artifacts", idx, "name"),
            "summary": "Duplicate artifact name",
            "msg": f"Artifact name '{name}' is duplicated.",
            "input": name,
        }

    # check fields for each artifact;
    ctx = get_workflow_context(workflow)

    for idx, artifact in enumerate(template.inputs.artifacts or ()):
        yield from prepend_loc(
            ("inputs", "artifacts", idx),
            _check_input_artifact(template, artifact, ctx),
        )


def _check_input_artifact(
    template: Template, artifact: Artifact, context: Context
) -> Iterable[Diagnosis]:
    # generic checks for all artifacts
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
            "from_",
            "fromExpression",
            "globalName",
        ],
    )

    # template type-specific: `path` should be present for container/script templates
    if template.type in ("container", "containerSet", "script"):
        if artifact.path is None:
            yield {
                "code": "M101",
                "loc": ("path",),
                "summary": "Missing required field 'path'",
                "msg": (
                    f"""
                    Field 'path' is required for artifact '{artifact.name}'.
                    Template '{template.name}' is a {template.type} template and it requires 'path' to specify file location.
                    """
                ),
            }
    else:
        if artifact.path is not None:
            yield {
                "code": "M102",
                "loc": ("path",),
                "summary": "Found redundant field 'path'",
                "msg": (
                    f"""
                    Field 'path' is invalid for artifact '{artifact.name}'.
                    Template '{template.name}' is a {template.type} template and does not accept 'path' field.
                    """
                ),
                "input": Field("path"),
            }

    # field-specific checks
    if artifact.raw:
        for diag in prepend_loc(
            ("raw", "data"),
            check_value_references(artifact.raw.data, context.parameters),
        ):
            match diag["code"]:
                case "VAR002":
                    diag["code"] = "TPL202"
                    if metadata := diag.get("ctx", {}).get("reference"):
                        ref = metadata["found:str"]
                        diag["msg"] = (
                            f"""
                            The parameter reference '{ref}' used in artifact '{artifact.name}' is invalid.
                            Note: Only parameter references are allowed here, even though this is an artifact object.
                            """
                        )
            yield diag
