from __future__ import annotations

import typing

from tugboat.constraints import require_all, require_exactly_one
from tugboat.core import hookimpl
from tugboat.parsers import parse_template, report_syntax_errors
from tugboat.references import get_template_context
from tugboat.utils import prepend_loc

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.references import Context
    from tugboat.schemas import (
        ContainerNode,
        ContainerTemplate,
        ScriptTemplate,
        Template,
        Workflow,
        WorkflowTemplate,
    )
    from tugboat.schemas.template import Probe
    from tugboat.types import Diagnosis

    type DocumentMap = dict[tuple[str | int, ...], str]


@hookimpl
def analyze_template(
    template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    """
    Perform the analysis of the container-based template:

    - Container template
    - Container set template
    - Script template

    This implementation only checks the specialized constraints for the
    container-based templates. The general constraints are checked by the
    generic template analyzer.
    """
    if not template.container and not template.script and not template.containerSet:
        return

    yield from check_input_artifacts(template)
    yield from check_output_parameters(template)
    yield from check_output_artifacts(template)

    ctx = get_template_context(workflow, template)
    yield from check_container_fields(template, ctx)


def check_input_artifacts(template: Template) -> Iterable[Diagnosis]:
    if not template.inputs:
        return

    for idx, artifact in enumerate(template.inputs.artifacts or ()):
        yield from require_all(
            model=artifact,
            loc=("inputs", "artifacts", idx),
            fields=["path"],
        )


def check_output_parameters(template: Template) -> Iterable[Diagnosis]:
    if not template.outputs:
        return

    for idx, parameter in enumerate(template.outputs.parameters or ()):
        loc = ("outputs", "parameters", idx)
        yield from require_all(
            model=parameter,
            loc=loc,
            fields=["valueFrom"],
        )

        if parameter.valueFrom:
            yield from require_all(
                model=parameter.valueFrom,
                loc=loc,
                fields=["path"],
            )


def check_output_artifacts(template: Template) -> Iterable[Diagnosis]:
    if not template.outputs:
        return

    for idx, artifact in enumerate(template.outputs.artifacts or ()):
        yield from require_all(
            model=artifact,
            loc=("outputs", "artifacts", idx),
            fields=["path"],
        )


def check_shared_fields(
    node: ContainerNode | ContainerTemplate | ScriptTemplate, ctx: Context
) -> Iterable[Diagnosis]:
    fields: DocumentMap = {}

    if node.image:
        fields["image",] = node.image

    for i, command in enumerate(node.command or []):
        fields["command", i] = command

    for i, envvar in enumerate(node.env or ()):
        yield from require_all(
            model=envvar,
            loc=("env", i),
            fields=["name"],
        )
        yield from require_exactly_one(
            model=envvar,
            loc=("env", i),
            fields=["value", "valueFrom"],
        )
        if envvar.valueFrom:
            yield from require_exactly_one(
                model=envvar.valueFrom,
                loc=("env", i, "valueFrom"),
                fields=[
                    "configMapKeyRef",
                    "fieldRef",
                    "resourceFieldRef",
                    "secretKeyRef",
                ],
            )

    for i, env_from in enumerate(node.envFrom or ()):
        yield from require_exactly_one(
            model=env_from,
            loc=("envFrom", i),
            fields=["configMapRef", "secretRef"],
        )

    if node.livenessProbe:
        yield from prepend_loc(
            ("livenessProbe",), _check_probe(node.livenessProbe, ctx)
        )

    if node.startupProbe:
        yield from prepend_loc(("startupProbe",), _check_probe(node.startupProbe, ctx))

    for i, mount in enumerate(node.volumeMounts or ()):
        ...  # TODO

    if node.workingDir:
        fields["workingDir",] = node.workingDir


def _check_probe(probe: Probe, ctx: Context) -> Iterable[Diagnosis]:
    yield from require_exactly_one(
        model=probe,
        loc=(),
        fields=["exec", "grpc", "httpGet", "tcpSocket"],
    )

    fields: DocumentMap = {}

    if probe.exec:
        for i, command in enumerate(probe.exec.command or ()):
            fields["exec", "command", i] = command

    if probe.grpc:
        if probe.grpc.service:
            fields["grpc", "service"] = probe.grpc.service

    if probe.httpGet:
        fields["httpGet", "path"] = probe.httpGet.path
        fields["httpGet", "port"] = str(probe.httpGet.port)

    if probe.tcpSocket:
        if probe.tcpSocket.host:
            fields["tcpSocket", "host"] = probe.tcpSocket.host
        fields["tcpSocket", "port"] = str(probe.tcpSocket.port)

    for loc, value in fields.items():
        doc = parse_template(value)
        yield from prepend_loc(loc, report_syntax_errors(doc))

        for node, ref, closest in ctx.parameters.filter_unknown(doc.iter_references()):
            yield {
                "code": "VAR002",
                "loc": loc,
                "summary": "Invalid reference",
                "msg": (f"Reference to unknown parameter '{ref}' in '{closest}'"),
                "input": str(node),
                "fix": node.format(closest),
            }


def check_container_fields(template: Template, context: Context) -> Iterable[Diagnosis]:
    if not template.container:
        return

    yield from prepend_loc(
        ("container",), check_shared_fields(template.container, context)
    )
