from __future__ import annotations

import typing
from typing import cast

from ruamel.yaml.comments import CommentedBase, CommentedMap, CommentedSeq

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    from ruamel.yaml.mergevalue import MergeValue


def is_anchor_node(parent_node: CommentedBase | None, key: int | str | None) -> bool:
    """
    Check if a child node is an anchor (&anchor).

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


def is_alias_node(parent_node: CommentedBase | None, key: int | str) -> bool:
    """
    Check if a child node is an alias (*anchor).

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


def get_value_linecol(
    parent_node: CommentedBase, key: int | str | None
) -> tuple[int, int] | None:
    """Find the start of the field value. Returns 0-based line and column numbers."""
    if isinstance(parent_node, CommentedMap):
        key = cast("str", key)
        if is_alias_node(parent_node, key):
            line, col = parent_node.lc.key(key)
            # adjust to point after the key name and colon
            col += len(str(key)) + 2
            return (line, col)
        else:
            return parent_node.lc.value(key)

    elif isinstance(parent_node, CommentedSeq):
        key = cast("int", key)
        # NOTE when the value is an alias, ruamel.yaml returns the line/col of the anchor
        if not is_alias_node(parent_node, key):
            return parent_node.lc.key(key)

    return None
