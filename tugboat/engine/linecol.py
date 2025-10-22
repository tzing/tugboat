from __future__ import annotations

import typing
from typing import cast

from ruamel.yaml.comments import CommentedBase, CommentedMap, CommentedSeq

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    from ruamel.yaml.mergevalue import MergeValue


def is_anchor_node(parent_node: CommentedBase, key: int | str) -> bool:
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


def is_alias_node(parent_node: CommentedBase, key: int | str) -> bool:
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


def calculate_substring_linecol(
    *,
    parent_node: CommentedBase,
    current_node: str,
    key: int | str,
    substring: str,
    indent_size: int,
) -> tuple[int, int] | None:
    """
    Calculate the line and column position of a substring within a scalar value.

    Parameters
    ----------
    parent_node : CommentedBase
        The parent node for enhanced positioning.
    current_node : str
        The current node containing the text.
    key : int | str
        The key in the parent node.
    substring: str
        The substring to find within the text.
    indent_size: int
        The assumed indentation size for the current node.

    Returns
    -------
    tuple[int, int] | None
        Line and column numbers (0-based), or None if substring not found or is alias.
    """
    # early exits
    if not substring:
        return None
    if is_alias_node(parent_node, key):
        return None
    if substring not in current_node:
        return None

    # dispatch based on scalar type
    if isinstance(current_node, LiteralScalarString):
        # literal block scalar (|)
        if isinstance(parent_node, CommentedSeq):
            return calculate_literal_substring_linecol_in_array(
                parent_node=cast("CommentedSeq", parent_node),
                current_node=current_node,
                key=cast("int", key),
                substring=substring,
            )
        if isinstance(parent_node, CommentedMap):
            return calculate_literal_substring_linecol_in_map(
                parent_node=cast("CommentedMap", parent_node),
                current_node=current_node,
                key=cast("str", key),
                substring=substring,
                indent_size=indent_size,
            )

    if isinstance(current_node, FoldedScalarString):
        # folded scalar (>) merges adjacent lines
        # so we can't tell the position of the substring reliably
        return None

    if isinstance(current_node, PlainScalarString):
        # plain scalar string type is found when the field contains anchor or alias
        # this breaks the logic of line/column calculation
        return None

    return None


def calculate_literal_substring_linecol_in_map(
    *,
    parent_node: CommentedMap,
    current_node: LiteralScalarString,
    key: str,
    substring: str,
    indent_size: int,
) -> tuple[int, int]:
    """
    ```yaml
    foo: |-
      Lorem ipsum dolor sit amet,
      consectetur adipiscing elit.
    ```

    * key line/col points to the position of `foo:`
    * value line/col points to the position of indicator `|-`
    """
    _, key_col, value_line, _ = cast("IntTuple", parent_node.lc.data[key])

    idx_substring = current_node.find(substring)
    cnt_lines_before = current_node.count("\n", 0, idx_substring)
    idx_last_newline = current_node.rfind("\n", 0, idx_substring)
    offset_col = idx_substring - idx_last_newline - 1

    return (
        value_line + cnt_lines_before + 1,
        key_col + indent_size + offset_col,
    )


def calculate_literal_substring_linecol_in_array(
    *,
    parent_node: CommentedSeq,
    current_node: LiteralScalarString,
    key: int,
    substring: str,
) -> tuple[int, int]:
    """
    ```yaml
    - |-
      Lorem ipsum dolor sit amet,
      consectetur adipiscing elit.
    ```

    * key line/col points to the position of indicator `|-`
    """
    value_line, value_col = cast("IntTuple", parent_node.lc.key(key))

    idx_substring = current_node.find(substring)
    cnt_lines_before = current_node.count("\n", 0, idx_substring)
    idx_last_newline = current_node.rfind("\n", 0, idx_substring)
    offset_col = idx_substring - idx_last_newline - 1

    return (
        value_line + cnt_lines_before + 1,
        value_col + offset_col,
    )
