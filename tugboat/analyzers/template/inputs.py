from __future__ import annotations

import collections
import json
import typing

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

    from tugboat.core import Diagnosis
    from tugboat.references import Context
    from tugboat.schemas import (
        Artifact,
        Parameter,
        Template,
        Workflow,
        WorkflowTemplate,
    )

    type DocumentMap = dict[tuple[str | int, ...], str]


@hookimpl(specname="analyze_template")
def check_input_parameters(
    template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    if not template.inputs:
        return

    ctx = get_workflow_context(workflow)

    # check fields for each parameter; also count the number of times each name appears
    parameters = collections.defaultdict(list)
    for idx, param in enumerate(template.inputs.parameters or []):
        loc = ("inputs", "parameters", idx)

        if param.name:
            parameters[param.name].append(loc)

        yield from prepend_loc(loc, check_input_parameter(param, ctx))

    # report duplicates
    for name, locs in parameters.items():
        if len(locs) > 1:
            for loc in locs:
                yield {
                    "code": "TPL002",
                    "loc": loc,
                    "summary": "Duplicate parameter name",
                    "msg": f"Parameter name '{name}' is duplicated.",
                    "input": name,
                }


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

    ctx = get_workflow_context(workflow)

    # check fields for each artifact; also count the number of times each name appears
    artifacts = collections.defaultdict(list)
    for idx, artifact in enumerate(template.inputs.artifacts or []):
        loc = ("inputs", "artifacts", idx)

        if artifact.name:
            artifacts[artifact.name].append(loc)

        yield from prepend_loc(loc, check_input_artifact(artifact, ctx))

    # report duplicates
    for name, locs in artifacts.items():
        if len(locs) > 1:
            for loc in locs:
                yield {
                    "code": "TPL003",
                    "loc": loc,
                    "summary": "Duplicate parameter name",
                    "msg": f"Parameter name '{name}' is duplicated.",
                    "input": name,
                }


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
