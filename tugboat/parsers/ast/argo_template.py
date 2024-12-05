from __future__ import annotations

import typing

from tugboat._vendor.pygments.token import Name, Punctuation, Text
from tugboat.parsers.ast.core import (
    Node,
    Unexpected,
    consume_whitespaces,
    next_lexeme_is,
)

if typing.TYPE_CHECKING:
    from collections.abc import Iterator

    from tugboat.parsers.ast.core import Lexeme

type ReferenceTuple = tuple[str, ...]


class Document(Node):

    @classmethod
    def parse(cls, lexemes: list[Lexeme]) -> Document:
        children = []
        while lexemes:
            for node_cls in [PlainText, SimpleReferenceTag, ExpressionTag, Unexpected]:
                if node := node_cls.parse(lexemes):
                    children.append(node)
                    break
        return cls(children=children)

    def iter_references(self) -> Iterator[tuple[SimpleReferenceTag, ReferenceTuple]]:
        """
        Iterate over all references in this document.
        """
        for child in self.children:
            if isinstance(child, SimpleReferenceTag):
                yield child, child.reference


class PlainText(Node):

    text: str

    @classmethod
    def parse(cls, lexemes: list[Lexeme]) -> PlainText | None:
        buffer = []
        while next_lexeme_is(lexemes, Text):
            _, _, text = lexemes.pop(0)
            buffer.append(text)
        return cls(text="".join(buffer)) if buffer else None


class SimpleReferenceTag(Node):

    raw: str
    """The raw text of the reference tag."""
    reference: ReferenceTuple
    """Reference to a variable."""

    @classmethod
    def parse(cls, lexemes: list[Lexeme]) -> SimpleReferenceTag | Unexpected | None:
        """
        Parse a simple reference tag.

        A typical lexemes sequence is like:

        .. code-block:: python

            [
                (0, Punctuation, "{{"),
                (2, Name.Variable, "foo"),
                (5, Punctuation, "."),
                (6, Name.Variable, "bar"),
                (9, Whitespace, "  "),
                (11, Punctuation, "}}"),
            ]
        """
        # early return
        if not next_lexeme_is(lexemes, token=Punctuation, text="{{"):
            return

        # consume the opening tag and whitespaces
        components = [
            lexemes.pop(0),
            *consume_whitespaces(lexemes),
        ]

        # consume the reference
        reference = []

        if next_lexeme_is(lexemes, Name.Variable):
            _, _, text = lexeme = lexemes.pop(0)
            components.append(lexeme)
            reference.append(text)

            while (
                True
                and next_lexeme_is(lexemes, Punctuation, ".")
                and next_lexeme_is(lexemes, Name.Variable, shift=1)
            ):
                # the dot
                lexeme = lexemes.pop(0)
                components.append(lexeme)

                # the name
                _, _, text = lexeme = lexemes.pop(0)
                components.append(lexeme)
                reference.append(text)

        # consume trailing whitespaces
        components += consume_whitespaces(lexemes)

        # expect the closing tag
        if not next_lexeme_is(lexemes, Punctuation, "}}"):
            if not lexemes or next_lexeme_is(lexemes, Text):
                return Unexpected.create(components, msg="expect closing tag '}}'")
            return Unexpected.create(components)

        components.append(lexemes.pop(0))  # consume the closing tag
        return cls(
            raw="".join(text for _, _, text in components),
            reference=tuple(reference),
        )

    def __str__(self) -> str:
        return self.raw

    @classmethod
    def format(cls, reference: ReferenceTuple) -> str | None:
        """
        Create a string representation of the reference in the same format as
        this reference tag type.
        """
        return "{{ " + ".".join(reference) + " }}" if reference else None


class ExpressionTag(Node):
    """
    This class recognizes the expression tag format and stores the literal content.
    """

    literal: str

    @classmethod
    def parse(cls, lexemes: list[Lexeme]) -> ExpressionTag | Unexpected | None:
        # early return
        if not next_lexeme_is(lexemes, token=Punctuation, text="{{="):
            return

        # consume the opening tag and whitespaces
        components = [
            lexemes.pop(0),
            *consume_whitespaces(lexemes),
        ]

        # consume all lexemes until the closing tag or the end of the lexemes
        while (
            True
            and lexemes
            and not next_lexeme_is(lexemes, Text)
            and not next_lexeme_is(lexemes, Punctuation, "}}")
        ):
            components.append(lexemes.pop(0))

        # expect the closing tag
        if not next_lexeme_is(lexemes, Punctuation, "}}"):
            if not lexemes or next_lexeme_is(lexemes, Text):
                return Unexpected.create(components, msg="expect closing tag '}}'")
            return Unexpected.create(components)

        components.append(lexemes.pop(0))  # consume the closing tag
        return cls(literal="".join(text for _, _, text in components))
