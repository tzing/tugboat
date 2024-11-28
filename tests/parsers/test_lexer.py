import textwrap

from tugboat._vendor.pygments.token import Name, Other, Punctuation, Text, Whitespace
from tugboat.parsers.lexer import ArgoTemplateLexer


class TestArgoTemplateLexer:

    def lex(self, source: str) -> list[tuple[str, str]]:
        lexer = ArgoTemplateLexer()
        tokens = []
        for _, token, text in lexer.get_tokens_unprocessed(source):
            tokens.append((token, text))
        return tokens

    def test_simple_reference(self):
        tokens = self.lex("{{ inputs.parameters.message}}")
        assert tokens == [
            (Punctuation, "{{"),
            (Whitespace, " "),
            (Name.Variable, "inputs"),
            (Punctuation, "."),
            (Name.Variable, "parameters"),
            (Punctuation, "."),
            (Name.Variable, "message"),
            (Punctuation, "}}"),
        ]

    def test_simple_reference_2(self):
        tokens = self.lex(
            textwrap.dedent(
                """
                Hello,
                This is a test for {{inputs.parameters.message }}!
                """
            ).strip()
        )
        assert tokens == [
            (Text, "Hello,\nThis is a test for "),
            (Punctuation, "{{"),
            (Name.Variable, "inputs"),
            (Punctuation, "."),
            (Name.Variable, "parameters"),
            (Punctuation, "."),
            (Name.Variable, "message"),
            (Whitespace, " "),
            (Punctuation, "}}"),
            (Text, "!"),
        ]

    def test_expression(self):
        # TODO rewrite this test after adding support for expressions
        tokens = self.lex("{{= inputs.parameters.message}}")
        assert tokens == [
            (Punctuation, "{{="),
            (Other, " inputs.parameters.message"),
            (Punctuation, "}}"),
        ]
