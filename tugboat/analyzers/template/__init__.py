from __future__ import annotations

import collections
import typing

from tugboat.analyzers.metrics import check_prometheus
from tugboat.constraints import require_exactly_one, require_non_empty
from tugboat.core import hookimpl
from tugboat.references import get_template_context
from tugboat.utils import prepend_loc

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.schemas import Template, Workflow, WorkflowTemplate
    from tugboat.types import Diagnosis

    type WorkflowCompatible = Workflow | WorkflowTemplate


@hookimpl
def analyze_template(template: Template) -> Iterable[Diagnosis]:
    yield from require_non_empty(
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
def check_steps(template: Template) -> Iterable[Diagnosis]:
    if not template.steps:
        return

    # check for duplicate step names
    step_names = collections.defaultdict(list)
    for idx_stage, stage in enumerate(template.steps or []):
        for idx_step, step in enumerate(stage):
            if step.name:
                step_names[step.name].append(("steps", idx_stage, idx_step, "name"))

    for name, locs in step_names.items():
        if len(locs) > 1:
            for loc in locs:
                yield {
                    "code": "STP101",
                    "loc": loc,
                    "summary": "Duplicate step name",
                    "msg": f"Step name '{name}' is duplicated.",
                    "input": name,
                }


@hookimpl(specname="analyze_template")
def check_metrics(
    template: Template, workflow: WorkflowCompatible
) -> Iterable[Diagnosis]:
    if not template.metrics:
        return

    # build context
    # some additional variables are available when emitting metrics in a template
    # https://argo-workflows.readthedocs.io/en/latest/variables/#metrics
    ctx = get_template_context(workflow, template)
    ctx.parameters |= {
        ("duration",),
        ("exitCode",),
        ("outputs", "result"),
        ("resourcesDuration", "cpu"),
        ("resourcesDuration", "memory"),
        ("retries",),
        ("status",),
    }
    if template.inputs:
        for param in template.inputs.parameters or ():
            ctx.parameters |= {("inputs", "parameters", param.name)}
    if template.outputs:
        for param in template.outputs.parameters or ():
            ctx.parameters |= {("outputs", "parameters", param.name)}

    # check metrics
    for idx, prom in enumerate(template.metrics.prometheus or ()):
        for diagnosis in prepend_loc(
            ("metrics", "prometheus", idx), check_prometheus(prom, ctx)
        ):
            match diagnosis["code"]:
                case "internal:invalid-metric-name":
                    diagnosis["code"] = "TPL301"
                case "internal:invalid-metric-label-name":
                    diagnosis["code"] = "TPL302"
                case "internal:invalid-metric-label-value":
                    diagnosis["code"] = "TPL303"
            yield diagnosis
