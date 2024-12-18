from __future__ import annotations

import json
import logging
import typing

from tugboat.references.cache import cache
from tugboat.references.context import AnyStr
from tugboat.references.template import get_template_context

if typing.TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any

    from tugboat.references.context import Context
    from tugboat.schemas import Step, Template, Workflow, WorkflowTemplate

logger = logging.getLogger(__name__)


@cache(32)
def get_step_context(
    workflow: Workflow | WorkflowTemplate, template: Template, step: Step
) -> Context:
    ctx = get_template_context(workflow, template)

    if step.withItems:
        ctx.parameters |= {("item",)}
        ctx.parameters |= {
            ("item", field) for field in _collect_item_fields(step.withItems)
        }

    if step.withParam:
        ctx.parameters |= {("item",)}

        fields = _collect_param_fields(step.withParam)
        if fields is None:
            logger.debug(
                "Failed to parse withParam in step %s. Allow `item.ANY`.", step.name
            )
            ctx.parameters |= {("item", AnyStr)}
        else:
            ctx.parameters |= {("item", field) for field in fields}

    if step.withSequence:
        ctx.parameters |= {("item",)}

    return ctx


def _collect_item_fields(with_items: Iterable[Any]) -> set[str]:
    fields = set()
    for item in with_items:
        if isinstance(item, dict):
            fields.update(item)
    return fields


def _collect_param_fields(s: str) -> set[str] | None:
    # try to parse the string as json array, or early return
    # it's common to use references in the withParam field
    try:
        data = json.loads(s)
    except Exception:
        return None
    if not isinstance(data, list):
        return None

    # collect all the fields in the json array
    fields = set()
    for item in data:
        if isinstance(item, dict):
            fields.update(item)

    return fields
