from __future__ import annotations

import typing

from tugboat.analyzers.constraints import require_exactly_one
from tugboat.core import hookimpl

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.core import Diagnostic
    from tugboat.schemas import Template, Workflow, WorkflowTemplate


@hookimpl
def analyze_template(template: Template) -> Iterable[Diagnostic]:
    yield from require_exactly_one(
        model=template,
        loc=(),
        fields=[
            "container",
            "dag",
            "data",
            "http",
            "script",
            "steps",
        ],
    )
