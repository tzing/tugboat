"""
This module provides the parser for Argo template syntax.

It parses the input text into an abstract syntax tree (AST) that can be used to
analyze the template and generate a report.
"""

from __future__ import annotations

__all__ = [
    "Document",
    "Node",
    "SimpleReferenceTag",
    "Unexpected",
    "parse_template",
    "report_syntax_errors",
]

import typing

import tugboat.parsers.ast.argo_template
import tugboat.parsers.lexer
from tugboat.parsers.ast import Document, Node, SimpleReferenceTag, Unexpected

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from tugboat.parsers.ast.core import Lexeme
    from tugboat.types import Diagnosis

_argo_template_lexer = None


def parse_template(text: str) -> Document:
    """Parse Argo template text into AST."""
    global _argo_template_lexer
    if not _argo_template_lexer:
        _argo_template_lexer = tugboat.parsers.lexer.ArgoTemplateLexer()

    lexemes: Iterable[Lexeme] = _argo_template_lexer.get_tokens_unprocessed(text)
    return tugboat.parsers.ast.argo_template.Document.parse(list(lexemes))


def report_syntax_errors(node: Node) -> Iterator[Diagnosis]:
    """Report errors in the AST."""
    # direct return if the node is an Unexpected node
    if isinstance(node, Unexpected):
        msg = f"Invalid syntax near '{node.text}'"
        if node.msg:
            msg += f": {node.msg}"
        yield {
            "code": "VAR001",
            "loc": (),
            "summary": "Syntax error",
            "msg": msg,
            "input": node.text,
        }

    # iterate over the children and yield any syntax errors
    i = 0
    while i < len(node.children):
        # try to find consecutive `Unexpected` nodes, if any
        #
        # The AST builder is intend to create a single Unexpected node for each
        # invalid token, so we need to group them together to provide a more
        # readable error message to the user.
        #
        # A special case is when the `Unexpected` node has a message, we yield
        # it as a single diagnosis. This is because the message is likely to be
        # more informative than the concatenated text of the nodes.
        unexpected_nodes = []
        while (
            i < len(node.children)
            and isinstance(child := node.children[i], Unexpected)
            and not child.msg
        ):
            unexpected_nodes.append(child)
            i += 1

        # if we found any, yield a single diagnosis
        if unexpected_nodes:
            text = "".join(node.text for node in unexpected_nodes)
            yield {
                "code": "VAR001",
                "loc": (),
                "summary": "Syntax error",
                "msg": (
                    f"""
                    Failed to parse the Argo workflow variable due to a syntax error.

                    This error is likely caused by an invalid character or an unexpected token in the variable definition.
                    The syntax error is near the following text: {text}
                    """
                ),
                "input": text,
            }
            # TODO
            # ideally we should yield each abnormal node as a separate diagnosis
            # but currently reporting does not look good, so we just return
            # the first one and skip the rest.
            return

        else:
            # recursively check the children
            yield from report_syntax_errors(node.children[i])
            i += 1
