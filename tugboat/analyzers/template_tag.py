"""
Parser for Argo template tags.

See Also
--------
Workflow Variables
   https://argo-workflows.readthedocs.io/en/latest/variables/
"""

from __future__ import annotations

import functools
import io
import textwrap
import typing

import lark

if typing.TYPE_CHECKING:
    from collections.abc import Iterator

    from tugboat.references import ReferenceCollection
    from tugboat.types import Diagnosis


@functools.cache
def _argo_template_tag_parser():
    return lark.Lark(
        r"""
        %import common.DIGIT
        %import common.LETTER
        %import common.WS

        ?start: template

        template: (_TEXT | expression_tag | simple_tag)+

        # ignore other text
        _TEXT: /[^{]+/
            | "{" /[^{]/

        # simple template tag
        simple_tag: "{{" WS? REF WS? "}}"
        REF: (LETTER | DIGIT | "_" | "-" | "." | "'" | "[" | "]")+

        # expression template tag
        expression_tag: "{{=" WS? _ANY WS? "}}"
        _ANY: /[^}]+/
        """
    )


@functools.lru_cache(32)
def parse_argo_template_tags(source: str) -> lark.Tree:
    """
    Parse Argo template tags in the given source string.

    Parameters
    ----------
    source : str
        The source string containing Argo template tags.

    Returns
    -------
    lark.Tree
        The parse tree representing the structure of the template tags.
    """
    parser = _argo_template_tag_parser()
    return parser.parse(source)
