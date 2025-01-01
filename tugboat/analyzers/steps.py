from __future__ import annotations

import collections
import typing

from tugboat.analyzers.template import check_input_artifact, check_input_parameter
from tugboat.core import hookimpl
from tugboat.references import get_step_context
from tugboat.utils import prepend_loc

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.core import Diagnosis
    from tugboat.schemas import Step, Template, Workflow, WorkflowTemplate

    type DocumentMap = dict[tuple[str | int, ...], str]


@hookimpl(specname="analyze_step")
def check_argument_parameters(
    step: Step, template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    if not step.arguments:
        return

    ctx = get_step_context(workflow, template, step)

    # check fields for each parameter; also count the number of times each name appears
    parameters = collections.defaultdict(list)
    for idx, param in enumerate(step.arguments.parameters or []):
        loc = ("arguments", "parameters", idx)

        if param.name:
            parameters[param.name].append(loc)

        yield from prepend_loc(loc, check_input_parameter(param, ctx))

    # report duplicates
    for name, locs in parameters.items():
        if len(locs) > 1:
            for loc in locs:
                yield {
                    "code": "STP002",
                    "loc": (*loc, "name"),
                    "summary": "Duplicate parameter name",
                    "msg": f"Parameter name '{name}' is duplicated.",
                    "input": name,
                }


@hookimpl(specname="analyze_step")
def check_argument_artifacts(
    step: Step, template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    if not step.arguments:
        return

    ctx = get_step_context(workflow, template, step)

    # check fields for each parameter; also count the number of times each name appears
    artifacts = collections.defaultdict(list)
    for idx, artifact in enumerate(step.arguments.artifacts or []):
        loc = ("arguments", "artifacts", idx)

        if artifact.name:
            artifacts[artifact.name].append(loc)

        yield from prepend_loc(loc, check_input_artifact(artifact, ctx))

    # report duplicates
    for name, locs in artifacts.items():
        if len(locs) > 1:
            for loc in locs:
                yield {
                    "code": "STP003",
                    "loc": (*loc, "name"),
                    "summary": "Duplicate artifact name",
                    "msg": f"Artifact name '{name}' is duplicated.",
                    "input": name,
                }
