from __future__ import annotations

import collections
import typing

from tugboat.analyzers.template import check_input_parameter
from tugboat.constraints import mutually_exclusive, require_all, require_exactly_one
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
                    "summary": "Duplicated parameter name",
                    "msg": f"Parameter name '{name}' is duplicated.",
                    "input": name,
                }
