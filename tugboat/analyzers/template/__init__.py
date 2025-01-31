from __future__ import annotations

import collections
import typing

from tugboat.constraints import require_exactly_one, require_non_empty
from tugboat.core import hookimpl

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.schemas import Template
    from tugboat.types import Diagnosis


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
