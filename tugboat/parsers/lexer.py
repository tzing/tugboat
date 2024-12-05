from __future__ import annotations

import typing

from tugboat._vendor.pygments.lexer import RegexLexer, words
from tugboat._vendor.pygments.token import Name, Other, Punctuation, Text, Whitespace

if typing.TYPE_CHECKING:
    from typing import ClassVar


class ArgoTemplateLexer(RegexLexer):
    """
    Argo template language lexer

    See also
    --------
    Template Tag Kinds
       https://argo-workflows.readthedocs.io/en/latest/variables/#template-tag-kinds
    """

    name: ClassVar = "Argo template"

    tokens: ClassVar = {
        "root": [
            (words(("{{=",)), Punctuation, "expression"),
            (words(("{{",)), Punctuation, "simple-reference"),
            (r"[^{]+", Text),
            (r"{", Text),
        ],
        "simple-reference": [
            (r"\s+", Whitespace),
            (r"\.", Punctuation),
            (r"[\w-]+", Name.Variable),
            (r"}}", Punctuation, "#pop"),
        ],
        "expression": [
            (r"[^}]+", Other),
            (r"}}", Punctuation, "#pop"),
        ],
    }
