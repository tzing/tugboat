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
from tugboat.references import get_task_context
from tugboat.types import Field
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
    from tugboat.schemas import DagTask, Step, Template, Workflow, WorkflowTemplate
    from tugboat.schemas.arguments import RelaxedArtifact, RelaxedParameter
    from tugboat.types import Diagnosis

    type WorkflowCompatible = Workflow | WorkflowTemplate

logger = logging.getLogger(__name__)


@hookimpl
def analyze_task(
    task: DagTask, template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    yield from require_exactly_one(
        model=task,
        loc=(),
        fields=["template", "templateRef", "inline"],
    )
    yield from mutually_exclusive(
        model=task,
        loc=(),
        fields=["withItems", "withParam", "withSequence"],
    )
    yield from mutually_exclusive(
        model=task,
        loc=(),
        fields=["depends", "dependencies"],
    )

    if task.onExit:
        yield {
            "code": "DAG901",
            "loc": ("onExit",),
            "summary": "Deprecated field",
            "msg": "Field 'onExit' is deprecated. Please use 'hooks[exit].template' instead.",
            "input": Field("onExit"),
        }


@hookimpl(specname="analyze_task")
def check_argument_parameters(
    task: DagTask, template: Template, workflow: WorkflowCompatible
) -> Iterable[Diagnosis]:
    if not task.arguments:
        return

    # report duplicate names
    for idx, name in find_duplicate_names(task.arguments.parameters or ()):
        yield {
            "code": "DAG102",
            "loc": ("arguments", "parameters", idx, "name"),
            "summary": "Duplicate parameter name",
            "msg": f"Parameter name '{name}' is duplicated.",
            "input": name,
        }


@hookimpl(specname="analyze_task")
def check_argument_artifacts(
    task: DagTask, template: Template, workflow: WorkflowCompatible
) -> Iterable[Diagnosis]:
    if not task.arguments:
        return

    # report duplicate names
    for idx, name in find_duplicate_names(task.arguments.artifacts or ()):
        yield {
            "code": "DAG103",
            "loc": ("arguments", "artifacts", idx, "name"),
            "summary": "Duplicate artifact name",
            "msg": f"Artifact name '{name}' is duplicated.",
            "input": name,
        }
