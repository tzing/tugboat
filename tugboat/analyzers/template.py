from __future__ import annotations

import typing

from tugboat.constraints import (
    accept_none,
    mutually_exclusive,
    require_all,
    require_exactly_one,
)
from tugboat.core import hookimpl

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.core import Diagnosis
    from tugboat.schemas import Template, Workflow, WorkflowTemplate


@hookimpl
def analyze_template(template: Template) -> Iterable[Diagnosis]:
    yield from require_all(
        model=template,
        loc=(),
        fields=["name"],
    )
    yield from require_exactly_one(
        model=template,
        loc=(),
        fields=[
            "container",
            "containerSet",
            "dag",
            "data",
            "http",
            "resource",
            "script",
            "steps",
            "suspend",
        ],
    )


@hookimpl(specname="analyze_template")
def check_input_parameters(
    template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    if not template.inputs:
        return

    # check fields for each parameter; also count the number of times each name appears
    parameters = {}
    for idx, param in enumerate(template.inputs.parameters or []):
        loc = ("inputs", "parameters", idx)

        yield from require_all(
            model=param,
            loc=loc,
            fields=["name"],
        )
        yield from mutually_exclusive(
            model=param,
            loc=loc,
            fields=["value", "valueFrom"],
        )

        if param.name:
            parameters.setdefault(param.name, []).append(loc)

        # TODO check expression

        if param.valueFrom:
            yield from require_exactly_one(
                model=param.valueFrom,
                loc=(*loc, "valueFrom"),
                fields=[
                    "configMapKeyRef",
                    "expression",
                    "parameter",
                ],
            )
            yield from accept_none(
                model=param.valueFrom,
                loc=(*loc, "valueFrom"),
                fields=[
                    "event",
                    "jqFilter",
                    "jsonPath",
                    "path",
                    "supplied",
                ],
            )

    # report duplicates
    for name, locs in parameters.items():
        if len(locs) > 1:
            for loc in locs:
                yield {
                    "code": "TPL002",
                    "loc": loc,
                    "summary": "Duplicated parameter name",
                    "msg": f"Parameter name '{name}' is duplicated.",
                    "input": name,
                }


@hookimpl(specname="analyze_template")
def check_input_artifacts(
    template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    if not template.inputs:
        return

    # check fields for each artifact; also count the number of times each name appears
    artifacts = {}
    for idx, artifact in enumerate(template.inputs.artifacts or []):
        loc = ("inputs", "artifacts", idx)

        yield from require_all(
            model=artifact,
            loc=loc,
            fields=["name"],
        )
        yield from mutually_exclusive(
            model=artifact,
            loc=loc,
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
            loc=loc,
            fields=[
                "archive",
                "archiveLogs",
                "artifactGC",
                "deleted",
            ],
        )

        if artifact.name:
            artifacts.setdefault(artifact.name, []).append(loc)

        # TODO check expression

    # report duplicates
    for name, locs in artifacts.items():
        if len(locs) > 1:
            for loc in locs:
                yield {
                    "code": "TPL003",
                    "loc": loc,
                    "summary": "Duplicated parameter name",
                    "msg": f"Parameter name '{name}' is duplicated.",
                    "input": name,
                }


@hookimpl(specname="analyze_template")
def check_output_parameters(
    template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    if not template.outputs:
        return

    # check fields for each parameter; also count the number of times each name appears
    parameters = {}
    for idx, param in enumerate(template.outputs.parameters or []):
        loc = ("outputs", "parameters", idx)

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

        if param.name:
            parameters.setdefault(param.name, []).append(loc)

        # TODO check expression

        if param.valueFrom:
            yield from require_exactly_one(
                model=param.valueFrom,
                loc=(*loc, "valueFrom"),
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

    # report duplicates
    for name, locs in parameters.items():
        if len(locs) > 1:
            for loc in locs:
                yield {
                    "code": "TPL004",
                    "loc": loc,
                    "summary": "Duplicated parameter name",
                    "msg": f"Parameter name '{name}' is duplicated.",
                    "input": name,
                }


@hookimpl(specname="analyze_template")
def check_output_artifacts(
    template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    if not template.outputs:
        return

    # check fields for each artifact; also count the number of times each name appears
    artifacts = {}
    for idx, artifact in enumerate(template.outputs.artifacts or []):
        loc = ("outputs", "artifacts", idx)

        yield from require_all(
            model=artifact,
            loc=loc,
            fields=["name"],
        )
        yield from require_exactly_one(
            model=artifact,
            loc=loc,
            fields=[
                "from_",
                "fromExpression",
                "path",
            ],
        )
        yield from mutually_exclusive(
            model=artifact,
            loc=loc,
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
            loc=loc,
            fields=[
                "git",
                "raw",
            ],
        )

        if artifact.name:
            artifacts.setdefault(artifact.name, []).append(loc)

        # TODO check expression

        if artifact.archive:
            yield from require_exactly_one(
                model=artifact.archive,
                loc=(*loc, "archive"),
                fields=[
                    "none",
                    "tar",
                    "zip",
                ],
            )

    # report duplicates
    for name, locs in artifacts.items():
        if len(locs) > 1:
            for loc in locs:
                yield {
                    "code": "TPL005",
                    "loc": loc,
                    "summary": "Duplicated parameter name",
                    "msg": f"Parameter name '{name}' is duplicated.",
                    "input": name,
                }
