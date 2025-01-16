from __future__ import annotations

__all__ = ["check_input_artifact", "check_input_parameter"]

import collections
import typing

from tugboat.analyzers.generic import check_model_fields_references
from tugboat.analyzers.template.inputs import (
    check_input_artifact,
    check_input_parameter,
)
from tugboat.constraints import require_all, require_exactly_one
from tugboat.core import hookimpl
from tugboat.references import get_template_context
from tugboat.utils import prepend_loc

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from pydantic import BaseModel

    from tugboat.schemas import Template, Workflow, WorkflowTemplate
    from tugboat.types import Diagnosis


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
def check_step_names(template: Template):
    if not template.steps:
        return

    steps = collections.defaultdict(list)
    for idx_stage, stage in enumerate(template.steps or []):
        for idx_step, step in enumerate(stage):
            if step.name:
                steps[step.name].append(("steps", idx_stage, idx_step, "name"))

    for name, locs in steps.items():
        if len(locs) > 1:
            for loc in locs:
                yield {
                    "code": "STP001",
                    "loc": loc,
                    "summary": "Duplicate step name",
                    "msg": f"Step name '{name}' is duplicated.",
                    "input": name,
                }
