from __future__ import annotations

import re
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
from ruamel.yaml.tokens import CommentToken

from tugboat.types import Field

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence
    from typing import Any

pattern_noqa_all = re.compile(r"[ ]*#[ ]*noqa(?:;|$)", re.IGNORECASE | re.MULTILINE)
pattern_noqa_line = re.compile(
    r"[ ]*#[ ]*noqa:[ ]*"  # prefix
    r"("
    r"[a-z]+\d+"  # first code
    r"(?:,[ ]*[A-Z]+[0-9]+)*"  # additional codes, separated by commas
    r")",
    re.IGNORECASE,
)


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
    if isinstance(parent_node, CommentedMap):
        try:
            key_line, key_col, value_line, value_col = parent_node.lc.data[key]
        except KeyError:
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
    # TODO handle the anchor in a list item

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
    if not isinstance(parent_node, CommentedBase):
        return False

    try:
        lc_data = parent_node.lc.data[key]
    except (AttributeError, KeyError, IndexError):
        return False

    if isinstance(parent_node, dict):
        key_line, key_col, value_line, value_col = lc_data

        if key_line != value_line:
            # heuristic: check if the value appears to be a multi-line string
            # if the value contains patterns that suggest multi-line content
            # and the value_line is adjacent to key_line, it's likely multi-line content, not alias
            value = parent_node[key]
            if isinstance(value, str) and value_line == key_line + 1:
                return False

            return True

    elif isinstance(parent_node, list):
        value_line, value_col = lc_data
        if value_line < parent_node.lc.line:
            return True
        # TODO need to handle the case where it references an item in a list

    return False


def get_suppression_codes(doc: CommentedMap, loc: Sequence[int | str]) -> Iterator[str]:
    """
    Get suppression codes from noqa comments at the location and all parent locations.

    This checks for noqa comments at the exact location and all parent locations.
    """
    current_node = doc

    # check root level comment first
    yield from _extract_noqa_codes_from_node(current_node, None)

    # navigate through the path, checking for noqa at each level
    for part in loc:
        # check if the current key has a noqa comment
        if isinstance(current_node, CommentedMap):
            yield from _extract_noqa_codes_from_node(current_node, part)

        # navigate to the next level
        try:
            current_node = current_node[part]  # type: ignore[reportIndexIssue]
        except (KeyError, IndexError, TypeError):
            break

        # check if the node itself has a noqa comment
        yield from _extract_noqa_codes_from_node(current_node, None)

    return []


def _extract_noqa_codes_from_node(
    node: CommentedBase, key: int | str | None = None
) -> Iterator[str]:
    """
    Extract series codes from noqa comment on a specific node or key.

    Parameters
    ----------
    node : CommentedBase
        The node to check for comments
    key : int | str | None
        If provided, check for key comment. If None, check node's own comment.

    Returns
    -------
    Iterator[str]
        Iterator of series codes found in the noqa comment.
    """
    if not isinstance(node, CommentedMap):
        return

    # try to find a comment on the key itself
    if key is not None and (key_comment_info := node.ca.items.get(key)):
        _, _, post_value_comment, pre_value_comments = key_comment_info
        if post_value_comment:
            yield from parse_noqa_codes(post_value_comment.value)

        if isinstance(node[key], int | float | str | bool):
            for comment in pre_value_comments or ():
                if isinstance(comment, CommentToken):
                    yield from parse_noqa_codes(comment.value)
                else:
                    yield from parse_noqa_codes(comment)

    # then, try to find an end-of-line comment on the node itself
    if node.ca.comment:
        post_comment, pre_comments = node.ca.comment
        if post_comment:
            yield from parse_noqa_codes(post_comment.value)


def parse_noqa_codes(text: str) -> Iterator[str]:
    """Parse series codes from a noqa comment."""
    if pattern_noqa_all.match(text):
        yield _Anything("Anything")
        return  # pragma: no cover; the caller may breaks the loop

    if m := pattern_noqa_line.match(text):
        for code in m.group(1).split(","):
            yield code.strip().upper()


class _Anything(str):
    """A string that matches anything."""

    def __eq__(self, other: Any):
        return True
