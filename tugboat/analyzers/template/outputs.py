from __future__ import annotations

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
from tugboat.references import get_template_context
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
def check_output_parameters(
    template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    if not template.outputs:
        return

    # report duplicate names
    for idx, name in report_duplicate_names(template.outputs.parameters or ()):
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
    sources: DocumentMap = {}

    # check fields
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

        if param.valueFrom.parameter:
            sources["valueFrom", "parameter"] = param.valueFrom.parameter

    # check references
    for loc, text in sources.items():
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
                    f"""The parameter reference '{".".join(ref)}' used in parameter '{param.name}' is invalid."""
                ),
                "input": str(node),
                "fix": node.format(closest),
            }


@hookimpl(specname="analyze_template")
def check_output_artifacts(
    template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    if not template.outputs:
        return

    # report duplicate names
    for idx, name in report_duplicate_names(template.outputs.artifacts or ()):
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
    artifact_sources: DocumentMap = {}

    # check fields
    yield from require_all(
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
        artifact_sources["from",] = artifact.from_

    # TODO artifact.fromExpression

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
                    f"""The artifact reference '{".".join(ref)}' used in artifact '{artifact.name}' is invalid."""
                ),
                "input": str(node),
                "fix": node.format(closest),
            }
