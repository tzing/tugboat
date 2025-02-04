from __future__ import annotations

import itertools
import logging
import typing

from tugboat.references.cache import cache
from tugboat.references.context import AnyStr
from tugboat.references.workflow import get_workflow_context

if typing.TYPE_CHECKING:
    from tugboat.references.context import Context
    from tugboat.schemas import Template, Workflow, WorkflowTemplate

logger = logging.getLogger(__name__)


@cache(16)
def get_template_context(
    workflow: Workflow | WorkflowTemplate, template: Template
) -> Context:
    """
    Returns a context with the available references for the given template.
    """
    ctx = get_workflow_context(workflow)

    # all template
    ctx.parameters |= {
        ("inputs", "parameters"),
        ("node", "name"),
        ("workflow", "status"),
        ("workflow", "failures"),
    }

    if template.inputs:
        ctx.parameters |= {
            ("inputs", "parameters", param.name)
            for param in template.inputs.parameters or []
        }
        ctx.artifacts |= {
            ("inputs", "artifacts", artifact.name)
            for artifact in template.inputs.artifacts or []
        }

    # container/script template
    if template.container or template.script or template.containerSet:
        ctx.parameters |= {("pod", "name")}

        if template.retryStrategy:
            ctx.parameters |= {("retries",)}

        if template.inputs:
            ctx.parameters |= {
                ("inputs", "artifacts", artifact.name, "path")
                for artifact in template.inputs.artifacts or []
            }

        if template.outputs:
            ctx.parameters |= {
                ("outputs", "artifacts", artifact.name, "path")
                for artifact in template.outputs.artifacts or []
            }
            ctx.parameters |= {
                ("outputs", "parameters", param.name, "path")
                for param in template.outputs.parameters or []
            }

    # add template-type specific references
    _add_step_references(ctx, template, workflow)
    # TODO dag template
    # TODO http template

    return ctx


def _add_step_references(
    ctx: Context,
    template: Template,
    workflow: Workflow | WorkflowTemplate,
):
    if not template.steps:
        return

    ctx.parameters |= {("steps", "name")}

    for step in itertools.chain.from_iterable(template.steps):
        # default step parameters
        ctx.parameters |= {
            ("steps", step.name, "id"),
            ("steps", step.name, "ip"),
            ("steps", step.name, "status"),
            ("steps", step.name, "exitCode"),
            ("steps", step.name, "startedAt"),
            ("steps", step.name, "finishedAt"),
            ("steps", step.name, "hostNodeName"),
            ("steps", step.name, "outputs", "result"),
        }

        # parallel steps
        if step.withItems or step.withParam:
            ctx.parameters |= {
                ("steps", step.name, "outputs", "parameters"),
            }

        # step outputs
        # when the referenced template is in the same workflow, we can resolve the outputs
        # otherwise, we can only assume the outputs are available
        reference_template = None
        if step.template:
            reference_template = workflow.template_dict.get(step.template)
        elif step.templateRef and step.templateRef.name == workflow.name:
            reference_template = workflow.template_dict.get(step.templateRef.template)
        elif step.inline:
            reference_template = step.inline

        if reference_template and reference_template.outputs:
            ctx.parameters |= {
                ("steps", step.name, "outputs", "parameters", param.name)
                for param in reference_template.outputs.parameters or []
                if param.name
            }
            ctx.artifacts |= {
                ("steps", step.name, "outputs", "artifacts", artifact.name)
                for artifact in reference_template.outputs.artifacts or []
                if artifact.name
            }

        if not reference_template:
            logger.debug(
                "The referenced template %s is not available. "
                "Allow `steps.%s.outputs.parameters.ANY` and `steps.%s.outputs.artifacts.ANY`.",
                step.template,
                step.name,
                step.name,
            )
            ctx.parameters |= {
                ("steps", step.name, "outputs", "parameters", AnyStr),
            }
            ctx.artifacts |= {
                ("steps", step.name, "outputs", "artifacts", AnyStr),
            }
