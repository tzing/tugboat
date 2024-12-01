"""
Utilities for building available references within the given scope.

See Also
--------
Reference
   https://argo-workflows.readthedocs.io/en/latest/variables/#reference
"""

from __future__ import annotations

import typing

from tugboat.references.cache import cache
from tugboat.references.context import Context

if typing.TYPE_CHECKING:
    from tugboat.schemas import Workflow, WorkflowTemplate


@cache(1)
def get_global_context() -> Context:
    """
    Returns a context with the available global references.
    """
    ctx = Context()
    ctx.parameters |= {
        ("workflow", "name"),
        ("workflow", "namespace"),
        ("workflow", "mainEntrypoint"),
        ("workflow", "serviceAccountName"),
        ("workflow", "uid"),
        ("workflow", "parameters", "json"),
        ("workflow", "annotations", "json"),
        ("workflow", "labels", "json"),
        ("workflow", "creationTimestamp"),
        ("workflow", "creationTimestamp", "RFC3339"),
        ("workflow", "priority"),
        ("workflow", "duration"),
        ("workflow", "scheduledTime"),
        ("workflow", "duration"),
    }
    return ctx


@cache(2)
def get_workflow_context_c(workflow: Workflow | WorkflowTemplate) -> Context:
    """
    Returns a context with the available references for the given workflow.

    This wraps :func:`get_workflow_context` with a cache, see :func:`cache`
    for more information.
    """
    return get_workflow_context(workflow)


def get_workflow_context(
    workflow: Workflow | WorkflowTemplate,
) -> Context:
    """
    Returns a context with the available references for the given workflow.
    """
    ctx = get_global_context()

    if workflow.spec.arguments:
        # workflow.parameters.<NAME>
        ctx.parameters |= {
            ("workflow", "parameters", param.name)
            for param in workflow.spec.arguments.parameters or []
        }

    for template in workflow.spec.templates or []:
        if template.outputs:
            # workflow.outputs.parameters.<NAME>
            ctx.parameters |= {
                ("workflow", "outputs", "parameters", param.globalName)
                for param in template.outputs.parameters or []
                if param.globalName
            }

            # workflow.outputs.artifacts.<NAME>
            ctx.artifacts |= {
                ("workflow", "outputs", "artifacts", artifact.globalName)
                for artifact in template.outputs.artifacts or []
                if artifact.globalName
            }

    return ctx
