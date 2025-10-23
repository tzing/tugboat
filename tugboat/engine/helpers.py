from __future__ import annotations

import re
import typing

from ruamel.yaml.comments import CommentedBase, CommentedMap
from ruamel.yaml.tokens import CommentToken

from tugboat.engine.types import DiagnosisModel

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from typing import Any

    from ruamel.yaml.error import MarkedYAMLError

pattern_noqa_all = re.compile(r"[ ]*#[ ]*noqa(?:;|$)", re.IGNORECASE | re.MULTILINE)
pattern_noqa_line = re.compile(
    r"[ ]*#[ ]*noqa:[ ]*"  # prefix
    r"("
    r"[a-z]+\d+"  # first code
    r"(?:,[ ]*[A-Z]+[0-9]+)*"  # additional codes, separated by commas
    r")",
    re.IGNORECASE,
)


def translate_marked_yaml_error(err: MarkedYAMLError) -> DiagnosisModel:
    """
    Translate a MarkedYAMLError into a more user-friendly format.

    Parameters
    ----------
    err : MarkedYAMLError
        The error to translate.

    Returns
    -------
    DiagnosisModel
        The translated error.
    """
    line = column = 1
    if err.problem_mark:
        line = err.problem_mark.line + 1
        column = err.problem_mark.column + 1

    msg = err.problem or err.context
    if msg and err.context_mark:
        msg += f"\n{err.context_mark}"  # context_mark is not a string

    return DiagnosisModel.model_validate(
        {
            "line": line,
            "column": column,
            "type": "error",
            "code": "F002",
            "loc": (),
            "summary": "Malformed YAML document",
            "msg": msg,
        }
    )


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
        post_comment, _pre_comments = node.ca.comment
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
