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
    assume_indent_size = 2

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
            assume_indent_size = current_node.lc.col - parent_node.lc.col

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
        assume_indent_size=assume_indent_size,
    ):
        return pos

    return fallback_position


def _calculate_substring_position(
    *,
    parent_node: CommentedMap | None,
    key: int | str | None,
    current_node: Any,
    substring: Any,
    assume_indent_size: int,
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
    assume_indent_size: int
        The assumed indentation size for the current node.

    Returns
    -------
    tuple[int, int] | None
        Line and column numbers (0-based), or None if substring not found or is alias.
    """
    if not substring or not isinstance(substring, str):
        return None

    text = str(current_node)
    substring_idx = text.find(substring)
    if substring_idx == -1:
        return None

    # early exit if this is an anchor or alias node
    if is_alias_node(parent_node, key):
        return None

    # calculate base line position
    key_line = key_col = value_line = value_col = None
    if parent_node:
        try:
            key_line, key_col, value_line, value_col = parent_node.lc.data.get(key)
        except (KeyError, IndexError):
            ...

    # determine column position based on scalar string type
    additional_offset = 0

    if isinstance(current_node, LiteralScalarString):
        # literal scalar (|) starts on the next line after the indicator
        key_col = cast("int", key_col)
        value_line = cast("int", value_line)
        value_col = cast("int", value_col)

        if lines_before := text[:substring_idx].count("\n"):
            last_newline_idx = text.rfind("\n", 0, substring_idx)
            column_offset = substring_idx - last_newline_idx - 1

            value_line += lines_before + 1
            value_col = key_col + assume_indent_size + column_offset
        else:
            value_line += 1
            value_col = key_col + assume_indent_size + substring_idx

        return (value_line, value_col)

    if isinstance(current_node, DoubleQuotedScalarString | SingleQuotedScalarString):
        additional_offset = 1

    if isinstance(current_node, FoldedScalarString):
        # folded scalar (>) merges adjacent lines so we can't tell the position
        # of the substring reliably, return None
        return None

    if isinstance(current_node, PlainScalarString):
        # plain scalar string type is found when the field contains anchor or alias
        # this breaks the logic of line/column calculation
        return None

    # only tell the position if it's *likely* a simple line in YAML
    if (
        True
        and key_line is not None
        and value_line is not None
        and text.find("\n", 0, substring_idx) == -1
        and key_line == value_line
        and not is_anchor_node(parent_node, key)
    ):
        column_offset = substring_idx
        value_col = cast("int", value_col)
        value_col += column_offset + additional_offset
        return (value_line, value_col)

    return None


def is_anchor_node(parent_node: CommentedMap | None, key: int | str | None) -> bool:
    """
    Check if a child node is an anchor (&anchor).

    Parameters
    ----------
    parent_node : CommentedMap | None
        The parent node.
    key : int | str | None
        The key in the parent node.

    Returns
    -------
    bool
        True if this is an anchor node, False otherwise.
    """
    if not parent_node or key is None:
        return False

    if (
        True
        and hasattr(parent_node[key], "yaml_anchor")
        and parent_node[key].yaml_anchor()
        and not is_alias_node(parent_node, key)
    ):
        return True

    return False


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
