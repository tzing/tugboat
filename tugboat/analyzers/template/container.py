from __future__ import annotations

import typing

from tugboat.constraints import require_all, require_exactly_one
from tugboat.core import hookimpl
from tugboat.utils import prepend_loc

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.schemas import Template, Workflow, WorkflowTemplate
    from tugboat.types import Diagnosis


@hookimpl
def analyze_template(
    template: Template, workflow: Workflow | WorkflowTemplate
) -> Iterable[Diagnosis]:
    """
    Perform the analysis of the container-based template:

    - Container template
    - Container set template
    - Script template

    This implementation only checks the specialized constraints for the
    container-based templates. The general constraints are checked by the
    generic template analyzer.
    """
    if not template.container and not template.script and not template.containerSet:
        return

    # RESERVED yield from check_input_parameters(template)
    yield from check_input_artifacts(template)
    yield from check_output_parameters(template)
    yield from check_output_artifacts(template)


def check_input_parameters(template: Template) -> Iterable[Diagnosis]:
    if not template.inputs:
        return

    yield NotImplemented


def check_input_artifacts(template: Template) -> Iterable[Diagnosis]:
    if not template.inputs:
        return

    for idx, artifact in enumerate(template.inputs.artifacts or ()):
        yield from require_all(
            model=artifact,
            loc=("inputs", "artifacts", idx),
            fields=["path"],
        )


def check_output_parameters(template: Template) -> Iterable[Diagnosis]:
    if not template.outputs:
        return

    for idx, parameter in enumerate(template.outputs.parameters or ()):
        loc = ("outputs", "parameters", idx)
        yield from require_all(
            model=parameter,
            loc=loc,
            fields=["valueFrom"],
        )

        if parameter.valueFrom:
            yield from require_all(
                model=parameter.valueFrom,
                loc=loc,
                fields=["path"],
            )


def check_output_artifacts(template: Template) -> Iterable[Diagnosis]:
    if not template.outputs:
        return

    for idx, artifact in enumerate(template.outputs.artifacts or ()):
        yield from require_all(
            model=artifact,
            loc=("outputs", "artifacts", idx),
            fields=["path"],
        )
