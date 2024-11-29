"""
Utilities for building available references within the given scope.

See Also
--------
Reference
   https://argo-workflows.readthedocs.io/en/latest/variables/#reference
"""

from __future__ import annotations

import copy
import functools
import typing

from pydantic import BaseModel, Field
from rapidfuzz.distance.DamerauLevenshtein import (
    distance as dameau_levenshtein_distance,
)
from rapidfuzz.distance.DamerauLevenshtein import (
    normalized_distance as dameau_levenshtein_normalized_distance,
)

from tugboat.utils import LruDict

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Collection

    from tugboat.schemas import Template, Workflow, WorkflowTemplate

type ReferenceTuple = tuple[str, ...]


def find_closest_match(
    target_reference: ReferenceTuple, candidate_references: Collection[ReferenceTuple]
) -> ReferenceTuple:
    """
    Find the closest match for a given reference in a list of reference.
    """
    # NOTE this algorithm is heuristic

    # group the candidates by their distance to the target reference
    distance_grouped_candidates: dict[int, list[ReferenceTuple]] = {}
    for candidate in candidate_references:
        dist = dameau_levenshtein_distance(target_reference, candidate)
        distance_grouped_candidates.setdefault(dist, []).append(candidate)

    # find the closest group
    closest_distance = min(distance_grouped_candidates.keys())
    closest_candidates = distance_grouped_candidates[closest_distance]

    if len(closest_candidates) == 1:
        return closest_candidates[0]

    # there are multiple candidates with the same distance, compare the elements
    # of the target reference with the candidates
    def _calculate_distance(candidate: ReferenceTuple) -> tuple[float, ...]:
        # calculate the normalized distance for each element
        base_distance = (
            dameau_levenshtein_normalized_distance(a, b)
            for a, b in zip(target_reference, candidate)
        )

        if len(target_reference) != len(candidate):
            # if the lengths are different, add a penalty to the distance
            return (*base_distance, 2.0)
        else:
            return tuple(base_distance)

    return min(closest_candidates, key=_calculate_distance)


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
