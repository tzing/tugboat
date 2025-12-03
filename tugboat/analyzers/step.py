from __future__ import annotations

import logging
import re
import typing

from rapidfuzz.process import extractOne

from tugboat.analyzers.template_tag import check_template_tags_recursive
from tugboat.constraints import accept_none, mutually_exclusive, require_all
from tugboat.core import get_plugin_manager, hookimpl
from tugboat.references import get_step_context
from tugboat.schemas import Arguments
from tugboat.types import Field
from tugboat.utils import find_duplicate_names, join_with_and, join_with_or, prepend_loc

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.references import Context
    from tugboat.schemas import (
        Artifact,
        DagTask,
        Parameter,
        Step,
        Template,
        Workflow,
        WorkflowTemplate,
    )
    from tugboat.types import Diagnosis

    type TaskCompatible = DagTask | Step
    type WorkflowCompatible = Workflow | WorkflowTemplate

logger = logging.getLogger(__name__)


@hookimpl
def analyze_step(
    step: Step, template: Template, workflow: WorkflowCompatible
) -> Iterable[Diagnosis]:
    yield from mutually_exclusive(
        step,
        fields=["template", "templateRef", "inline"],
        require_one=True,
    )
    yield from mutually_exclusive(
        step,
        fields=["withItems", "withParam", "withSequence"],
    )

    if step.onExit:
        yield {
            "code": "STP901",
            "loc": ("onExit",),
            "summary": "Deprecated field",
            "msg": "Field 'onExit' is deprecated. Please use 'hooks[exit].template' instead.",
            "input": Field("onExit"),
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
            ("arguments", "parameters", idx),
            check_argument_parameter_fields(param, ctx),
        )


def check_argument_parameter_fields(
    param: Parameter, context: Context
) -> Iterable[Diagnosis]:
    yield from require_all(param, fields=["name"])
    yield from mutually_exclusive(param, fields=["value", "valueFrom"])

    if param.valueFrom:
        yield from mutually_exclusive(
            param.valueFrom,
            loc=("valueFrom",),
            fields=[
                "configMapKeyRef",
                "expression",
                "parameter",
            ],
            require_one=True,
        )
        yield from accept_none(
            param.valueFrom,
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

    for diag in check_template_tags_recursive(param, context.parameters):
        match diag["code"]:
            case "VAR201":
                diag["code"] = "STP301"
                if metadata := diag.get("ctx", {}).get("reference"):
                    ref = metadata["found:str"]
                    diag["msg"] = (
                        f"The parameter reference '{ref}' used in parameter '{param.name}' is invalid."
                    )
        yield diag


@hookimpl(specname="analyze_step")
def check_argument_parameters_usage(
    step: TaskCompatible, workflow: WorkflowCompatible
) -> Iterable[Diagnosis]:
    # early exit: referenced template not found
    ref_template = _get_template_by_ref(step, workflow)
    if not ref_template:
        return

    # prepare arguments in case not provided
    if step.arguments:
        arguments = step.arguments
    else:
        arguments = Arguments()

    # check for redundant parameters
    if ref_template.inputs:
        expected_params = set(ref_template.inputs.parameter_dict)
    else:
        expected_params = set()

    for idx, param in enumerate(arguments.parameters or ()):
        if param.name and param.name not in expected_params:
            suggestion = None
            if result := extractOne(param.name, expected_params):
                suggestion, _, _ = result

            yield {
                "type": "warning",  # redundant parameter does not break the workflow
                "code": "STP304",
                "loc": ("arguments", "parameters", idx, "name"),
                "summary": "Unexpected parameter",
                "msg": f"Parameter '{param.name}' is not expected by the template '{ref_template.name}'.",
                "input": param.name,
                "fix": suggestion,
            }

    # check for missing parameters
    if ref_template.inputs:
        required_params = set()
        for name, model in ref_template.inputs.parameter_dict.items():
            if model.default is None and model.value is None:
                required_params.add(name)

        missing_parameters = required_params.difference(arguments.parameter_dict)
        if missing_parameters:
            yield {
                "code": "STP305",
                "loc": ("arguments", "parameters"),
                "summary": "Missing parameters",
                "msg": (
                    f"Parameters {join_with_and(missing_parameters)} are required by the template '{ref_template.name}' but are not provided."
                ),
                "input": Field("parameters"),
            }


def _get_template_by_ref(
    step: TaskCompatible, workflow: WorkflowCompatible
) -> Template | None:
    if step.template:
        return workflow.template_dict.get(step.template)
    if step.templateRef and step.templateRef.name == workflow.metadata.name:
        return workflow.template_dict.get(step.templateRef.template)
    return None


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
            ("arguments", "artifacts", idx),
            check_argument_artifact_fields(artifact, ctx),
        )


def check_argument_artifact_fields(
    artifact: Artifact, context: Context
) -> Iterable[Diagnosis]:
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
        for diag in check_template_tags_recursive(
            artifact, mixed_references, include=["from_"]
        ):
            match diag["code"]:
                case "VAR201":
                    diag["code"] = "STP302"
                    if metadata := diag.get("ctx", {}).get("reference"):
                        ref = metadata["found:str"]
                        diag["msg"] = (
                            f"The reference '{ref}' used in artifact '{artifact.name}' is invalid."
                        )
            yield diag

    # TODO fromExpression

    if artifact.raw:
        for diag in check_template_tags_recursive(
            artifact, context.parameters, include=["raw"]
        ):
            match diag["code"]:
                case "VAR201":
                    diag["code"] = "STP303"
                    if metadata := diag.get("ctx", {}).get("reference"):
                        ref = metadata["found:str"]
                        diag["msg"] = (
                            f"""
                            The parameter reference '{ref}' used in artifact '{artifact.name}' is invalid.
                            Note: Only parameter references are allowed here, even though this is an artifact object.
                            """
                        )
            yield diag


@hookimpl(specname="analyze_step")
def check_argument_artifact_usage(
    step: TaskCompatible, workflow: WorkflowCompatible
) -> Iterable[Diagnosis]:
    # early exit: referenced template not found
    ref_template = _get_template_by_ref(step, workflow)
    if not ref_template:
        return

    # prepare arguments in case not provided
    if step.arguments:
        arguments = step.arguments
    else:
        arguments = Arguments()

    # check for redundant artifacts
    if ref_template.inputs:
        expected_artifacts = set(ref_template.inputs.artifact_dict)
    else:
        expected_artifacts = set()

    for idx, artifact in enumerate(arguments.artifacts or ()):
        if artifact.name and artifact.name not in expected_artifacts:
            suggestion = None
            if result := extractOne(artifact.name, expected_artifacts):
                suggestion, _, _ = result

            yield {
                "type": "warning",  # redundant artifact does not break the workflow
                "code": "STP306",
                "loc": ("arguments", "artifacts", idx, "name"),
                "summary": "Unexpected artifact",
                "msg": f"Artifact '{artifact.name}' is not expected by the template '{ref_template.name}'.",
                "input": artifact.name,
                "fix": suggestion,
            }

    # check for missing artifacts
    if ref_template.inputs:
        required_artifacts = set()
        for name, model in ref_template.inputs.artifact_dict.items():
            if (
                False
                # -- optional artifact --
                or model.optional
                # -- defined in template --
                or model.artifactory
                or model.azure
                or model.gcs
                or model.git
                or model.hdfs
                or model.http
                or model.oss
                or model.raw
                or model.s3
            ):
                continue
            required_artifacts.add(name)

        missing_artifacts = required_artifacts.difference(arguments.artifact_dict)
        if missing_artifacts:
            yield {
                "code": "STP307",
                "loc": ("arguments", "artifacts"),
                "summary": "Missing artifacts",
                "msg": (
                    f"Artifacts {join_with_and(missing_artifacts)} are required by the template '{ref_template.name}' but are not provided."
                ),
                "input": Field("artifacts"),
            }


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
        if step.templateRef.name == workflow.metadata.name:
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
    yield from check_template_tags_recursive(
        step,
        ctx.parameters,
        exclude=["arguments", "inline", "withItems", "withSequence"],
    )


@hookimpl(specname="analyze_step")
def check_inline_template(
    step: TaskCompatible, workflow: WorkflowCompatible
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
