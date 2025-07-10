from __future__ import annotations

import typing
from typing import cast

from ruamel.yaml.comments import CommentedBase, CommentedMap
from ruamel.yaml.scalarstring import (
    DoubleQuotedScalarString,
    FoldedScalarString,
    LiteralScalarString,
    PlainScalarString,
    SingleQuotedScalarString,
)

from tugboat.types import Field

if typing.TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any


def get_line_column(
    doc: CommentedMap, loc: Sequence[int | str], value: Any | Field | None
) -> tuple[int, int]:
    """
    Get the line and column number for a given location in the YAML document.

    Parameters
    ----------
    doc : CommentedMap
        The parsed YAML document.
    loc : Sequence[int | str]
        Path to the location in the document.
    value : Any | Field | None
        Value to locate a more specific position, if applicable. If a Field is
        provided, this function will attempt to find the position of the key in
        the map. Otherwise, it will search for the value in the field.

    Returns
    -------
    tuple[int, int]
        Line and column numbers (0-based).
    """
    # navigate through the path
    current_node = doc
    parent_node = None
    key = None
    fallback_position = (0, 0)

    for key in loc:
        parent_node = current_node

        try:
            current_node = current_node[key]  # type: ignore[reportIndexIssue]
        except (KeyError, IndexError, TypeError):
            # navigation failed, use fallback position from parent
            if parent_node and hasattr(parent_node, "lc"):
                fallback_position = (parent_node.lc.line, parent_node.lc.col)
            break

        if isinstance(current_node, CommentedBase) and current_node.lc:
            fallback_position = (current_node.lc.line, current_node.lc.col)

    # if the value is 'Field' type, return the position of the key
    if isinstance(value, Field):
        try:
            parent_node = cast("CommentedMap", parent_node)
            return parent_node.lc.key(value)
        except (KeyError, AttributeError):
            return fallback_position

    # for the rest of the cases, default to the start of the field value
    if isinstance(parent_node, CommentedMap):
        try:
            # for aliases, we need to get the position of the alias key, not the anchor
            if is_alias_node(parent_node, key):
                fallback_position = parent_node.lc.key(key)
                # adjust to point after the key name and colon
                fallback_position = (
                    fallback_position[0],
                    fallback_position[1] + len(str(key)) + 2,
                )
            else:
                fallback_position = parent_node.lc.value(key)
        except (KeyError, AttributeError):
            ...

    # calculate substring position if value is a string
    if pos := _calculate_substring_position(
        parent_node=parent_node,
        key=key,
        current_node=current_node,
        substring=value,
        fallback_position=fallback_position,
    ):
        return pos

    return fallback_position


def _calculate_substring_position(
    *,
    parent_node: CommentedMap | None,
    key: int | str | None,
    current_node: Any,
    substring: Any,
    fallback_position: tuple[int, int],
) -> tuple[int, int] | None:
    """
    Calculate the line and column position of a substring within a scalar value.

    Parameters
    ----------
    parent_node : CommentedMap | None
        The parent node for enhanced positioning.
    key : int | str | None
        The key in the parent node.
    current_node : Any
        The current node containing the text.
    substring: str
        The substring to find within the text.
    fallback_position : tuple[int, int]
        The fallback position if precise calculation fails.

    Returns
    -------
    tuple[int, int] | None
        Line and column numbers (0-based), or None if substring not found or is alias.
    """
    if not substring or not isinstance(substring, str):
        return None

    text = str(current_node)
    substring_index = text.find(substring)
    if substring_index == -1:
        return None

    # check if this is an alias - if so, return None to fall back to fallback position
    if is_alias_node(parent_node, key):
        return None

    lines_before = text[:substring_index].count("\n")

    # calculate base line position
    if lines_before > 0:
        last_newline_pos = text.rfind("\n", 0, substring_index)
        column_offset = substring_index - last_newline_pos - 1
        line_pos = fallback_position[0] + lines_before
    else:
        column_offset = substring_index
        line_pos = fallback_position[0]

    # determine column position based on scalar string type
    if isinstance(current_node, LiteralScalarString | FoldedScalarString):
        # block scalars (| and >): account for block indentation
        col_pos = column_offset + 4
        # block scalars content starts on the next line after the indicator
        line_pos = fallback_position[0] + 1 + lines_before
        return (line_pos, col_pos)

    if isinstance(current_node, DoubleQuotedScalarString | SingleQuotedScalarString):
        # quoted strings (" and '): account for opening quote and anchor offset
        anchor_offset = get_anchor_offset(parent_node, key)
        if lines_before > 0:
            col_pos = column_offset
        else:
            col_pos = fallback_position[1] + 1 + column_offset + anchor_offset
        return (line_pos, col_pos)

    if isinstance(current_node, PlainScalarString):
        # plain scalar string: check for anchor offset
        anchor_offset = get_anchor_offset(parent_node, key)
        if lines_before > 0:
            col_pos = column_offset
        else:
            col_pos = fallback_position[1] + column_offset + anchor_offset
        return (line_pos, col_pos)

    # handle regular strings (not ScalarString instances)
    anchor_offset = get_anchor_offset(parent_node, key)
    if lines_before > 0:
        col_pos = column_offset
    else:
        col_pos = fallback_position[1] + column_offset + anchor_offset

    return (line_pos, col_pos)


def is_alias_node(parent_node: CommentedMap | None, key: int | str | None) -> bool:
    """
    Check if a child node is an alias (*anchor).

    Parameters
    ----------
    parent_node : CommentedMap | None
        The parent node.
    key : int | str | None
        The key in the parent node.

    Returns
    -------
    bool
        True if this is an alias node, False otherwise.
    """
    if not parent_node or key is None:
        return False

    try:
        lc_data = parent_node.lc.data.get(key)
    except (AttributeError, KeyError, IndexError, TypeError):
        return False

    if lc_data:
        key_line, key_col, value_line, value_col = lc_data

        if key_line != value_line:
            # heuristic: check if the value appears to be a multi-line string
            # if the value contains patterns that suggest multi-line content
            # and the value_line is adjacent to key_line, it's likely multi-line content, not alias
            value = parent_node[key]
            if isinstance(value, str) and value_line == key_line + 1:
                return False

            return True

    return False


def get_anchor_offset(parent_node: CommentedMap | None, key: int | str | None) -> int:
    """
    Get the column offset introduced by anchor symbol (&anchor).

    Parameters
    ----------
    parent_node : CommentedMap | None
        The parent node.
    key : int | str | None
        The key in the parent node.

    Returns
    -------
    int
        The column offset for anchor symbol, 0 if not an anchor.
    """
    if not parent_node or key is None:
        return 0

    if (
        not is_alias_node(parent_node, key)
        and hasattr(parent_node[key], "yaml_anchor")
        and (anchor := parent_node[key].yaml_anchor())
    ):
        # calculate offset: "&" + anchor_name + " " = 1 + len(anchor_name) + 1
        return len(anchor.value) + 2

    return 0
