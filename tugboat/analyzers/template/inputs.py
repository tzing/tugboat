from __future__ import annotations

import json
import typing

from tugboat.analyzers.generic import report_duplicate_names
from tugboat.constraints import (
    accept_none,
    mutually_exclusive,
    require_all,
    require_exactly_one,
)
from tugboat.core import hookimpl
from tugboat.parsers import parse_template, report_syntax_errors
from tugboat.references import get_workflow_context
from tugboat.utils import prepend_loc

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

    type DocumentMap = dict[tuple[str | int, ...], str]


@hookimpl(specname="analyze_template")
def check_input_parameters(
    template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    if not template.inputs:
        return

    # report duplicate names
    for idx, name in report_duplicate_names(template.inputs.parameters or ()):
        yield {
            "code": "TPL002",
            "loc": ("inputs", "parameters", idx, "name"),
            "summary": "Duplicate parameter name",
            "msg": f"Parameter name '{name}' is duplicated.",
            "input": name,
        }

    # check fields for each parameter
    ctx = get_workflow_context(workflow)

    for idx, param in enumerate(template.inputs.parameters or ()):
        yield from prepend_loc(
            ("inputs", "parameters", idx), check_input_parameter(param, ctx)
        )


def check_input_parameter(param: Parameter, context: Context) -> Iterable[Diagnosis]:
    sources: DocumentMap = {}

    # check fields
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

    if param.value:
        if isinstance(param.value, int | bool):
            sources["value",] = json.dumps(param.value)
        else:
            sources["value",] = param.value

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

        if param.valueFrom.parameter:
            sources["valueFrom", "parameter"] = param.valueFrom.parameter

        # TODO check expression

    # check references
    for loc, value in sources.items():
        doc = parse_template(value)
        yield from prepend_loc(loc, report_syntax_errors(doc))

        for node, ref, closest in context.parameters.filter_unknown(
            doc.iter_references()
        ):
            yield {
                "code": "VAR002",
                "loc": loc,
                "summary": "Invalid reference",
                "msg": (
                    f"The parameter reference '{".".join(ref)}' used in parameter "
                    f"'{param.name}' is invalid."
                ),
                "input": str(node),
                "fix": node.format(closest),
            }


@hookimpl(specname="analyze_template")
def check_input_artifacts(
    template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    if not template.inputs:
        return

    # report duplicate names
    for idx, name in report_duplicate_names(template.inputs.artifacts or ()):
        yield {
            "code": "TPL003",
            "loc": ("inputs", "artifacts", idx, "name"),
            "summary": "Duplicate parameter name",
            "msg": f"Parameter name '{name}' is duplicated.",
            "input": name,
        }

    # check fields for each artifact;
    ctx = get_workflow_context(workflow)

    for idx, artifact in enumerate(template.inputs.artifacts or []):
        yield from prepend_loc(
            ("inputs", "artifacts", idx), check_input_artifact(artifact, ctx)
        )


def check_input_artifact(artifact: Artifact, context: Context) -> Iterable[Diagnosis]:
    param_sources: DocumentMap = {}
    artifact_sources: DocumentMap = {}

    # check fields
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
        artifact_sources["from",] = artifact.from_

    # TODO fromExpression

    if artifact.raw:
        param_sources["raw", "data"] = artifact.raw.data

    # check references
    for loc, text in artifact_sources.items():
        doc = parse_template(text)
        yield from prepend_loc(loc, report_syntax_errors(doc))

        for node, ref, closest in context.artifacts.filter_unknown(
            doc.iter_references()
        ):
            yield {
                "code": "VAR002",
                "loc": loc,
                "summary": "Invalid reference",
                "msg": (
                    f"The artifact reference '{".".join(ref)}' used in artifact '{artifact.name}' is invalid."
                ),
                "input": str(node),
                "fix": node.format(closest),
            }

    for loc, text in param_sources.items():
        doc = parse_template(text)
        yield from prepend_loc(loc, report_syntax_errors(doc))

        for node, ref, closest in context.parameters.filter_unknown(
            doc.iter_references()
        ):
            yield {
                "code": "VAR002",
                "loc": loc,
                "summary": "Invalid reference",
                "msg": (
                    f"""
                    The parameter reference '{".".join(ref)}' used in artifact '{artifact.name}' is invalid.
                    Note: Only parameter references are allowed here, even though this is an artifact object.
                    """
                ),
                "input": str(node),
                "fix": node.format(closest),
            }
