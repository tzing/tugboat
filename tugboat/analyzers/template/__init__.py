from __future__ import annotations

__all__ = ["check_input_artifact", "check_input_parameter"]

import collections
import typing

from tugboat.analyzers.template.inputs import (
    check_input_artifact,
    check_input_parameter,
)
from tugboat.constraints import require_all, require_exactly_one
from tugboat.core import hookimpl
from tugboat.parsers import parse_template, report_syntax_errors
from tugboat.references import get_template_context
from tugboat.utils import prepend_loc

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.core import Diagnosis
    from tugboat.schemas import Template, Workflow, WorkflowTemplate

    type DocumentMap = dict[tuple[str | int, ...], str]


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
                    "summary": "Duplicated step name",
                    "msg": f"Step name '{name}' is duplicated.",
                    "input": name,
                }


@hookimpl(specname="analyze_template")
def check_field_references(
    template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    """
    Check fields that may contains references.

    Currently only part of the fields are checked. See the list below:

    Implemented:

    - `container`
      - `args`
      - `command`
      - `image`
      - `stdin`
      - `workingDir`

    - `script`
      - `command`
      - `image`
      - `source`
      - `workingDir`

    Intended excluded:

    - `inputs` - handled in `check_input_parameters` and `check_input_artifacts` above
    - `outputs` - handled in `check_output_parameters` and `check_output_artifacts` above
    - `steps` - handled separately in another hook
    """
    # collect fields
    fields: DocumentMap = {}

    if template.container:
        for i, command in enumerate(template.container.command or []):
            fields["container", "command", i] = command
        for i, arg in enumerate(template.container.args or []):
            fields["container", "args", i] = arg

        fields["container", "image"] = template.container.image
        if template.container.workingDir:
            fields["container", "workingDir"] = template.container.workingDir

    if template.script:
        for i, command in enumerate(template.script.command or []):
            fields["script", "command", i] = command

        fields["script", "image"] = template.script.image
        fields["script", "source"] = template.script.source
        if template.script.workingDir:
            fields["script", "workingDir"] = template.script.workingDir

    if not fields:
        return

    # check each field for template syntax and references
    ctx = get_template_context(workflow, template)

    for loc, value in fields.items():
        doc = parse_template(value)
        yield from prepend_loc(loc, report_syntax_errors(doc))

        for node, ref, closest in ctx.parameters.filter_unknown(doc.iter_references()):
            yield {
                "code": "VAR002",
                "loc": loc,
                "summary": "Invalid reference",
                "msg": (
                    f"""The parameter reference '{".".join(ref)}' used in template '{template.name}' is invalid."""
                ),
                "input": str(node),
                "fix": node.format(closest),
            }
