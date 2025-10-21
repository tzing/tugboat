from __future__ import annotations

import typing
from typing import cast

from ruamel.yaml.comments import CommentedBase, CommentedMap

from tugboat.types import Field

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import Any

    from ruamel.yaml.mergevalue import MergeValue


def is_anchor_node(parent_node: CommentedBase | None, key: int | str | None) -> bool:
    """
    Check if a child node is an anchor (&anchor).

    Parameters
    ----------
    parent_node : CommentedBase | None
        The parent node.
    key : int | str | None
        The key in the parent node.

    Returns
    -------
    bool
        True if this is an anchor node, False otherwise.
    """
    try:
        target_node = parent_node[key]  # type: ignore[reportIndexIssue]
    except (KeyError, IndexError, TypeError):
        return False

    anchor: Callable | None = getattr(target_node, "yaml_anchor", None)
    if anchor and anchor() and not is_alias_node(parent_node, key):
        return True

    return False


def is_alias_node(parent_node: CommentedBase | None, key: int | str | None) -> bool:
    """
    Check if a child node is an alias (*anchor).

    Parameters
    ----------
    parent_node : CommentedBase | None
        The parent node.
    key : int | str | None
        The key in the parent node.

    Returns
    -------
    bool
        True if this is an alias node, False otherwise.
    """
    if key is None:
        return False
    if not isinstance(parent_node, CommentedBase):
        return False

    if merge_values := getattr(parent_node, "_yaml_merge", None):
        merge_values = cast("MergeValue", merge_values)
        for value_dict in merge_values.value:
            if key in value_dict:
                return True

    try:
        child_lc = parent_node.lc.data[key]
    except (AttributeError, KeyError, IndexError):
        return False

    if isinstance(parent_node, dict):
        key_line, _, value_line, _ = child_lc
        return value_line < key_line

    elif isinstance(parent_node, list):
        value_line, _ = child_lc
        if value_line < parent_node.lc.line:
            return True

        if (prev_idx := cast("int", key) - 1) >= 0:
            prev_value_line, _ = parent_node.lc.data[prev_idx]
            if value_line < prev_value_line:
                return True

    return False
