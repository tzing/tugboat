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


def check_template_tags(
    source: str, references: ReferenceCollection
) -> Iterator[Diagnosis]:
    """
    Check the given source string for errors in Argo template tags.

    Parameters
    ----------
    source : str
        The source string containing Argo template tags.
    references : ReferenceCollection
        The current active references.

    Yields
    ------
    Diagnosis
        A diagnosis for each error found.
    """
    try:
        tree = parse_argo_template_tags(source)

    except lark.UnexpectedInput as e:
        with io.StringIO() as buf:
            buf.write("The field contains a syntax error for Argo template tags.")
            buf.write("\n\n")
            buf.write("The parser reported the errors near:\n\n")
            buf.write(textwrap.indent(e.get_context(source), "  "))

            match type(e):
                case lark.UnexpectedCharacters:
                    buf.write(
                        "\n"
                        "This error is usually caused by invalid characters in the template tag.\n"
                        "Please ensure that the template tags are correctly formatted."
                    )
                case lark.UnexpectedEOF:
                    buf.write(
                        "\n"
                        "This error is usually caused by an incomplete template tag.\n"
                        "Please ensure that all template tags are properly closed."
                    )

            message = buf.getvalue()

        yield {
            "code": "VAR001",
            "loc": (),
            "summary": "Syntax error",
            "msg": message,
            "input": source,
        }
        return
