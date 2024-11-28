from __future__ import annotations

import copy
import functools
import typing

from pydantic import BaseModel, Field

from tugboat.utils import LruDict

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    from tugboat.schemas import Workflow, WorkflowTemplate

type ReferenceTuple = tuple[str, ...]


class Context(BaseModel):
    parameters: set[ReferenceTuple] = Field(default_factory=set)
    artifacts: set[ReferenceTuple] = Field(default_factory=set)


def cache(max_size: int):
    """
    Decorator to cache the results of a function.

    This is a specialized version of :py:func:`functools.lru_cache` that uses the
    input object IDs as keys and returns a copy of the cached value.

    It uses input object IDs as keys because the input objects are Pydantic
    models, which are mutable. Due to this, the cache key is based on the object
    IDs, but developers should be aware that this can lead to unexpected behavior
    if the same object is passed multiple times.
    """

    def _decorator[**P](func: Callable[P, Context]) -> Callable[P, Context]:
        store = LruDict(max_size=max_size)

        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            key = tuple(id(arg) for arg in args)
            if (value := store.get(key)) is None:
                store[key] = value = func(*args, **kwargs)
            return copy.deepcopy(value)

        return _wrapper

    return _decorator


@cache(1)
def get_global_context() -> Context:
    """
    Returns a context with the available global references.

    See Also
    --------
    Global Reference
       https://argo-workflows.readthedocs.io/en/latest/variables/#global
    """
    return Context(
        parameters={
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
    )


@cache(2)
def get_workflow_context_c(workflow: Workflow | WorkflowTemplate) -> Context:
    """
    Returns a context with the available references for the given workflow.
    This is a cached version of :func:`get_workflow_context`.
    """
    return get_workflow_context(workflow)


def get_workflow_context(
    workflow: Workflow | WorkflowTemplate,
) -> Context:
    """
    Returns a context with the available references for the given workflow.

    See Also
    --------
    Global Reference
       https://argo-workflows.readthedocs.io/en/latest/variables/#global
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
