from __future__ import annotations

import typing
from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict, Field

from tugboat._vendor.pygments.token import Whitespace

if typing.TYPE_CHECKING:
    from typing import Self

    from tugboat._vendor.pygments.token import _TokenType

    type Lexeme = tuple[int, _TokenType, str]


class Node(ABC, BaseModel):
    """Base class for AST nodes."""

    model_config = ConfigDict(frozen=True)

    children: list[Node] = Field(default_factory=list)

    @classmethod
    @abstractmethod
    def parse(cls, lexemes: list[Lexeme]) -> Node | None:
        """
        Parse a list of tokens into AST. This method may pop items from the list
        when it consumes them.

        Parameters
        ----------
        lexemes : list[Lexeme]
            The list of tokens to parse.

        Returns
        -------
        The AST node or None if parsing failed.
        """


class Unexpected(Node):
    """Node to represent unparsable tokens or syntax errors."""

    pos: int
    text: str
    msg: str | None = None

    @classmethod
    def parse(cls, lexemes: list[Lexeme]) -> Self | None:
        if not lexemes:
            return
        pos, _, text = lexemes.pop(0)
        return cls(pos=pos, text=text)

    @classmethod
    def create(cls, lexemes: list[Lexeme], msg: str | None = None) -> Self:
        start_pos, _, _ = lexemes[0]
        return cls(
            pos=start_pos,
            text="".join(text for _, _, text in lexemes),
            msg=msg,
        )


def next_lexeme_is(
    lexemes: list[Lexeme],
    token: _TokenType | None = None,
    text: str | None = None,
    shift: int = 0,
) -> bool:
    """Check if the next token in the list matches the given token or text."""
    if len(lexemes) <= 0:
        return False

    _, next_token, next_text = lexemes[shift]
    if token is not None and next_token not in token:
        return False
    if text is not None and next_text != text:
        return False
    return True


def consume_whitespaces(lexemes: list[Lexeme]) -> list[Lexeme]:
    """Pop all leading whitespace tokens from the lexemes stream."""
    buffer = []
    while next_lexeme_is(lexemes, Whitespace):
        buffer.append(lexemes.pop(0))
    return buffer
