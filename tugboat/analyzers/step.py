from __future__ import annotations

import logging
import re
import typing

from rapidfuzz.process import extractOne

from tugboat.constraints import (
    accept_none,
    mutually_exclusive,
    require_exactly_one,
    require_non_empty,
)
from tugboat.core import get_plugin_manager, hookimpl
from tugboat.references import get_step_context
from tugboat.utils import (
    check_model_fields_references,
    check_value_references,
    critique_relaxed_artifact,
    critique_relaxed_parameter,
    find_duplicate_names,
    join_with_or,
    prepend_loc,
)

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.references import Context
    from tugboat.schemas import Step, Template, Workflow, WorkflowTemplate
    from tugboat.schemas.arguments import RelaxedArtifact, RelaxedParameter
    from tugboat.types import Diagnosis

    type WorkflowCompatible = Workflow | WorkflowTemplate

logger = logging.getLogger(__name__)


@hookimpl
def analyze_step(
    step: Step, template: Template, workflow: WorkflowCompatible
) -> Iterable[Diagnosis]:
    yield from require_exactly_one(
        model=step,
        loc=(),
        fields=["template", "templateRef", "inline"],
    )
    yield from mutually_exclusive(
        model=step,
        loc=(),
        fields=["withItems", "withParam", "withSequence"],
    )

    if step.onExit:
        yield {
            "code": "STP901",
            "loc": ("onExit",),
            "summary": "Deprecated field",
            "msg": "Field 'onExit' is deprecated. Please use 'hooks[exit].template' instead.",
            "input": "onExit",
        }


@hookimpl(specname="analyze_step")
def check_argument_parameters(
    step: Step, template: Template, workflow: WorkflowCompatible
) -> Iterable[Diagnosis]:
    if not step.arguments:
        return

    # report duplicate names
    for idx, name in find_duplicate_names(step.arguments.parameters or ()):
        yield {
            "code": "STP102",
            "loc": ("arguments", "parameters", idx, "name"),
            "summary": "Duplicate parameter name",
            "msg": f"Parameter name '{name}' is duplicated.",
            "input": name,
        }

    # check fields for each parameter
    ctx = get_step_context(workflow, template, step)

    for idx, param in enumerate(step.arguments.parameters or ()):
        yield from prepend_loc(
            ("arguments", "parameters", idx), _check_argument_parameter(param, ctx)
        )


def _check_argument_parameter(
    param: RelaxedParameter, context: Context
) -> Iterable[Diagnosis]:
    yield from require_non_empty(
        model=param,
        loc=(),
        fields=["name"],
    )
    yield from mutually_exclusive(
        model=param,
        loc=(),
        fields=["value", "valueFrom"],
    )
    yield from critique_relaxed_parameter(param)

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
                ctx = typing.cast("dict", diag.get("ctx"))
                ref = ".".join(ctx["ref"])
                diag["code"] = "STP301"
                diag["msg"] = (
                    f"The parameter reference '{ref}' used in parameter '{param.name}' is invalid."
                )
        yield diag


@hookimpl(specname="analyze_step")
def check_argument_artifacts(
    step: Step, template: Template, workflow: WorkflowCompatible
) -> Iterable[Diagnosis]:
    if not step.arguments:
        return

    # report duplicate names
    for idx, name in find_duplicate_names(step.arguments.artifacts or ()):
        yield {
            "code": "STP103",
            "loc": ("arguments", "artifacts", idx, "name"),
            "summary": "Duplicate artifact name",
            "msg": f"Artifact name '{name}' is duplicated.",
            "input": name,
        }

    # check fields for each parameter
    ctx = get_step_context(workflow, template, step)

    for idx, artifact in enumerate(step.arguments.artifacts or []):
        yield from prepend_loc(
            ("arguments", "artifacts", idx), _check_argument_artifact(artifact, ctx)
        )


def _check_argument_artifact(
    artifact: RelaxedArtifact, context: Context
) -> Iterable[Diagnosis]:
    yield from require_non_empty(
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
    yield from critique_relaxed_artifact(artifact)

    if artifact.from_:
        # `from` value can be either wrapped by the cruely brackets or not
        from_ = artifact.from_.strip()

        # when it is unwrapped, it should be a reference to an artifact
        # EXAMPLE> artifact: inputs.artifacts.artifact-1
        if re.fullmatch(r"[a-zA-Z0-9.-]+", from_):
            ref = tuple(from_.split("."))
            if ref not in context.artifacts:
                closest = context.artifacts.find_closest(ref)
                yield {
                    "code": "STP302",
                    "loc": ("from",),
                    "summary": "Invalid reference",
                    "msg": f"The reference '{from_}' used in artifact '{artifact.name}' is invalid.",
                    "input": artifact.from_,
                    "fix": ".".join(closest),
                }

        # when it is wrapped, it may be a reference to a parameter or an artifact
        mixed_references = context.parameters + context.artifacts
        for diag in prepend_loc(
            ("from",), check_value_references(from_, mixed_references)
        ):
            match diag["code"]:
                case "VAR002":
                    ctx = typing.cast("dict", diag.get("ctx"))
                    ref = ".".join(ctx["ref"])
                    diag["code"] = "STP302"
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
                    ctx = typing.cast("dict", diag.get("ctx"))
                    ref = ".".join(ctx["ref"])
                    diag["code"] = "STP303"
                    diag["msg"] = (
                        f"""
                        The parameter reference '{ref}' used in artifact '{artifact.name}' is invalid.
                        Note: Only parameter references are allowed here, even though this is an artifact object.
                        """
                    )
            yield diag


@hookimpl(specname="analyze_step")
def check_referenced_template(
    step: Step, template: Template, workflow: WorkflowCompatible
) -> Iterable[Diagnosis]:
    if step.template:
        yield from prepend_loc(
            ("template",),
            _check_referenced_template(step.template, template, workflow),
        )

    elif step.templateRef:
        if step.templateRef.name == workflow.name:
            yield from prepend_loc(
                ("templateRef", "template"),
                _check_referenced_template(
                    step.templateRef.template, template, workflow
                ),
            )
        else:
            logger.debug(
                "Step '%s': Referenced template '%s' is not the same as current workflow '%s'. Skipping.",
                step.name,
                step.templateRef.name,
                workflow.name,
            )


def _check_referenced_template(
    target_template_name: str, template: Template, workflow: WorkflowCompatible
) -> Iterable[Diagnosis]:
    if target_template_name == template.name:
        yield {
            "type": "warning",
            "code": "STP201",
            "loc": (),
            "summary": "Self-referencing",
            "msg": "Self-referencing may cause infinite recursion.",
            "input": target_template_name,
        }

    if target_template_name not in workflow.template_dict:
        templates = set(workflow.template_dict)
        templates -= {template.name}
        templates = sorted(templates)

        suggestion = None
        if result := extractOne(target_template_name, templates):
            suggestion, _, _ = result

        yield {
            "code": "STP202",
            "loc": (),
            "summary": "Template not found",
            "msg": f"""
                Template '{target_template_name}' does not exist in the workflow.
                Available templates: {join_with_or(templates)}
                """,
            "input": target_template_name,
            "fix": suggestion,
        }


@hookimpl(specname="analyze_step")
def check_fields_references(
    step: Step, template: Template, workflow: WorkflowCompatible
) -> Iterable[Diagnosis]:
    ctx = get_step_context(workflow, template, step)
    yield from check_model_fields_references(
        step,
        ctx.parameters,
        exclude=["arguments", "inline", "withItems", "withSequence"],
    )


@hookimpl(specname="analyze_step")
def check_inline_template(
    step: Step, workflow: WorkflowCompatible
) -> Iterable[Diagnosis]:
    if not step.inline:
        return

    # check inline template type
    for diagnosis in accept_none(
        model=step.inline,
        loc=("inline",),
        fields=("dag", "steps"),
    ):
        diagnosis["code"] = "STP401"
        diagnosis["summary"] = "Invalid inline template type"
        diagnosis["msg"] = (
            """
            Nested steps or DAGs will result in an invalid step.
            Please use simple steps or a DAG at the top level of the template.
            """
        )
        yield diagnosis

    # check inline template definitions
    pm = get_plugin_manager()

    for diagnosis in prepend_loc.from_iterables(
        ("inline",),
        pm.hook.analyze_template(template=step.inline, workflow=workflow),
    ):
        if diagnosis["loc"] == ("inline", "name"):
            # template name is not required
            continue
        if diagnosis["loc"][:2] in {("inline", "steps"), ("inline", "dag")}:
            # step templates or dag templates are not allowed
            continue

        yield diagnosis
