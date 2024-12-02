import textwrap

from dirty_equals import IsInstance

import tugboat.parsers.lexer
from tugboat._vendor.pygments.token import Error, Name, Punctuation, Text, Whitespace
from tugboat.parsers.ast.argo_template import (
    Document,
    ExpressionTag,
    PlainText,
    SimpleReferenceTag,
)
from tugboat.parsers.ast.core import Unexpected


class TestDocument:

    def parse(self, text: str) -> Document:
        text = textwrap.dedent(text).strip()

        lexer = tugboat.parsers.lexer.ArgoTemplateLexer()
        lexemes = list(lexer.get_tokens_unprocessed(text))

        doc = Document.parse(lexemes)
        assert isinstance(doc, Document)
        assert lexemes == []

        return doc

    def test_plain_text(self):
        doc = self.parse("hello world")
        assert doc.children == [PlainText(text="hello world")]
        assert list(doc.iter_references()) == []

    def test_reference_tag(self):
        doc = self.parse("{{ foo }}")
        assert doc.children == [SimpleReferenceTag(raw="{{ foo }}", reference=("foo",))]
        assert list(doc.iter_references()) == [
            (IsInstance(SimpleReferenceTag), ("foo",))
        ]

    def test_expression_tag(self):
        doc = self.parse("{{= foo(bar, baz) }}")
        assert doc.children == [ExpressionTag(literal="{{= foo(bar, baz) }}")]

    def test_mixed(self):
        doc = self.parse("Hello, {{ foo }}! I'm {{= bar }}.")
        assert doc.children == [
            PlainText(text="Hello, "),
            SimpleReferenceTag(raw="{{ foo }}", reference=("foo",)),
            PlainText(text="! I'm "),
            ExpressionTag(literal="{{= bar }}"),
            PlainText(text="."),
        ]
        assert list(doc.iter_references()) == [
            (IsInstance(SimpleReferenceTag), ("foo",))
        ]

    def test_error_1(self):
        doc = self.parse("Hello {{ foo !")
        assert doc.children == [
            PlainText(text="Hello "),
            Unexpected(pos=6, text="{{ foo "),
            Unexpected(pos=13, text="!"),
        ]

    def test_error_2(self):
        doc = self.parse("Hello {{ foo.}} !")
        assert doc.children == [
            PlainText(text="Hello "),
            Unexpected(pos=6, text="{{ foo"),
            Unexpected(pos=12, text="."),
            Unexpected(pos=13, text="}}"),
            PlainText(text=" !"),
        ]


class TestPlainText:

    def test_matched_1(self):
        lexemes = [
            (-1, Text, "Hello"),
            (-1, Text, " "),
            (-1, Text, "world"),
        ]

        node = PlainText.parse(lexemes)
        assert lexemes == []

        assert isinstance(node, PlainText)
        assert node.text == "Hello world"

    def test_matched_2(self):
        lexemes = [
            (-1, Text, "Hello"),
            (-1, Error, "#"),
        ]

        node = PlainText.parse(lexemes)
        assert len(lexemes) == 1

        assert isinstance(node, PlainText)
        assert node.text == "Hello"


class TestSimpleReferenceTag:

    def test_matched_1(self):
        lexemes = [
            (-1, Punctuation, "{{"),
            (-1, Whitespace, "  "),
            (-1, Name.Variable, "foo"),
            (-1, Punctuation, "}}"),
        ]

        node = SimpleReferenceTag.parse(lexemes)
        assert lexemes == []

        assert isinstance(node, SimpleReferenceTag)
        assert str(node) == "{{  foo}}"
        assert node.reference == ("foo",)

    def test_matched_2(self):
        lexemes = [
            (-1, Punctuation, "{{"),
            (-1, Name.Variable, "foo"),
            (-1, Punctuation, "."),
            (-1, Name.Variable, "bar"),
            (-1, Whitespace, "  "),
            (-1, Punctuation, "}}"),
        ]

        node = SimpleReferenceTag.parse(lexemes)
        assert lexemes == []

        assert isinstance(node, SimpleReferenceTag)
        assert str(node) == "{{foo.bar  }}"
        assert node.reference == ("foo", "bar")

    def test_skipped(self):
        lexemes = [
            (-1, Punctuation, "{{="),
        ]
        assert SimpleReferenceTag.parse(lexemes) is None

    def test_error_general(self):
        lexemes = [
            (-1, Punctuation, "{{"),
            (-1, Name.Variable, "foo"),
            (-1, Punctuation, "."),
            (-1, Punctuation, "}}"),
        ]

        node = SimpleReferenceTag.parse(lexemes)

        assert isinstance(node, Unexpected)
        assert node.text == "{{foo"

    def test_error_missing_closing_tag(self):
        lexemes = [
            (-1, Punctuation, "{{"),
            (-1, Name.Variable, "foo"),
            (-1, Punctuation, "."),
            (-1, Name.Variable, "bar"),
        ]

        node = SimpleReferenceTag.parse(lexemes)
        assert lexemes == []

        assert isinstance(node, Unexpected)
        assert node.text == "{{foo.bar"
        assert node.msg == "expect closing tag '}}'"

    def test_format(self):
        assert SimpleReferenceTag.format(("foo", "bar")) == "{{ foo.bar }}"
        assert SimpleReferenceTag.format(("foo",)) == "{{ foo }}"
