from __future__ import annotations

import typing

from tugboat.constraints import require_all, require_exactly_one, require_non_empty
from tugboat.core import hookimpl
from tugboat.references import get_template_context
from tugboat.utils import check_model_fields_references, prepend_loc

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
    from tugboat.types import Diagnosis


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
    if template.container:
        yield from prepend_loc(
            ("container",), check_shared_fields(template, ctx, template.container)
        )
    if template.script:
        yield from prepend_loc(
            ("script",), check_shared_fields(template, ctx, template.script)
        )
    if template.containerSet:
        for i, container in enumerate(template.containerSet.containers or ()):
            yield from prepend_loc(
                ("containerSet", "containers", i),
                check_shared_fields(template, ctx, container),
            )


def check_input_artifacts(template: Template) -> Iterable[Diagnosis]:
    if not template.inputs:
        return

    for idx, artifact in enumerate(template.inputs.artifacts or ()):
        yield from require_non_empty(
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
            yield from require_non_empty(
                model=parameter.valueFrom,
                loc=(*loc, "valueFrom"),
                fields=["path"],
            )


def check_output_artifacts(template: Template) -> Iterable[Diagnosis]:
    if not template.outputs:
        return

    for idx, artifact in enumerate(template.outputs.artifacts or ()):
        yield from require_non_empty(
            model=artifact,
            loc=("outputs", "artifacts", idx),
            fields=["path"],
        )


def check_shared_fields(
    template: Template,
    context: Context,
    node: ContainerNode | ContainerTemplate | ScriptTemplate,
) -> Iterable[Diagnosis]:
    for i, envvar in enumerate(node.env or ()):
        yield from require_non_empty(
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

    for diag in check_model_fields_references(node, context.parameters):
        match diag["code"]:
            case "VAR002":
                ctx = typing.cast(dict, diag.get("ctx"))
                ref = ".".join(ctx["ref"])
                diag["msg"] = (
                    f"The parameter reference '{ref}' used in template '{template.name}' is invalid."
                )
        yield diag
