from tugboat.engine import yaml_parser
from tugboat.engine.linecol import is_alias_node


class TestIsAliasNode:

    def test_str(self):
        doc = yaml_parser.load(
            """
            anchor: &anchor
              Lorem ipsum dolor sit amet

            bar: *anchor

            baz:
              Lorem ipsum dolor sit amet,
              consectetur adipiscing elit.
            """
        )

        assert is_alias_node(doc, "bar") is True
        assert is_alias_node(doc, "baz") is False

    def test_array_1(self):
        doc = yaml_parser.load(
            """
            anchor: &anchor
              Lorem ipsum dolor sit amet

            array:
              - *anchor
              - consectetur adipiscing elit
              - *anchor
            """
        )

        assert is_alias_node(doc, "array") is False
        assert is_alias_node(doc["array"], 0) is True
        assert is_alias_node(doc["array"], 1) is False
        assert is_alias_node(doc["array"], 2) is True

    def test_array_2(self):
        doc = yaml_parser.load(
            """
            array:
              - &anchor
                Lorem ipsum dolor sit amet
              - consectetur adipiscing elit
              - *anchor
            """
        )

        assert is_alias_node(doc, "array") is False
        assert is_alias_node(doc["array"], 0) is False
        assert is_alias_node(doc["array"], 1) is False
        assert is_alias_node(doc["array"], 2) is True

    def test_map_1(self):
        doc = yaml_parser.load(
            """
            anchor: &anchor
              foo: bar

            map: *anchor
            """
        )

        assert is_alias_node(doc, "map") is True
        assert is_alias_node(doc, "anchor") is False

    def test_map_2(self):
        doc = yaml_parser.load(
            """
            anchor: &anchor
              foo: bar

            map:
              <<: *anchor
              baz: qux
            """
        )

        assert is_alias_node(doc, "map") is False
        assert is_alias_node(doc["map"], "foo") is True
        assert is_alias_node(doc["map"], "baz") is False

        assert is_alias_node(doc, "anchor") is False

    def test_error(self):
        doc = yaml_parser.load("foo: bar")
        assert is_alias_node(doc, "no-this-key") is False
        assert is_alias_node(doc, None) is False
        assert is_alias_node(None, "key") is False
