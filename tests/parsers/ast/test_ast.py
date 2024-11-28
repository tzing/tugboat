from tugboat._vendor.pygments.token import Other
from tugboat.parsers.ast.core import Unexpected


class TestUnexpected:
    def test_parse_1(self):
        lexemes = [(0, Other, "hello"), (5, Other, "world")]

        node = Unexpected.parse(lexemes)
        assert len(lexemes) == 1

        assert isinstance(node, Unexpected)
        assert node.pos == 0
        assert node.text == "hello"

    def test_parse_2(self):
        node = Unexpected.parse([])
        assert node is None

    def test_create_1(self):
        lexemes = [(0, Other, "hello"), (5, Other, "world")]
        node = Unexpected.create(lexemes)
        assert isinstance(node, Unexpected)
        assert node.pos == 0
        assert node.text == "helloworld"
        assert node.msg is None

    def test_create_2(self):
        lexemes = [(0, Other, "hello"), (5, Other, "world")]
        node = Unexpected.create(lexemes, "test error")
        assert isinstance(node, Unexpected)
        assert node.msg == "test error"
