import textwrap

from tugboat.engine import yaml_parser
from tugboat.engine.linecol import (
    get_value_linecol,
    is_alias_node,
    is_anchor_node,
)


class TestIsAnchorNode:

    def test_dict(self):
        doc = yaml_parser.load(
            """
            array:
              - &anchor
                Lorem ipsum dolor sit amet
              - consectetur adipiscing elit
              - *anchor

            map:
              foo: &foo
                Lorem ipsum dolor sit amet
              bar: *foo
            """
        )

        assert is_anchor_node(doc, "array") is False
        assert is_anchor_node(doc["array"], 0) is True
        assert is_anchor_node(doc["array"], 1) is False
        assert is_anchor_node(doc["array"], 2) is False

        assert is_anchor_node(doc, "map") is False
        assert is_anchor_node(doc["map"], "foo") is True
        assert is_anchor_node(doc["map"], "bar") is False

    def test_error(self):
        doc = yaml_parser.load("foo: bar")
        assert not is_anchor_node(doc, "key")


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


class TestGetValueLineColumn:

    def test_map(self):
        doc = yaml_parser.load(
            textwrap.dedent(
                """
                map:
                  foo: &foo
                    Lorem ipsum dolor sit amet
                  bar:    consectetur adipiscing elit.

                  array:
                    - item
                  alias: *foo
                """
            )
        )

        assert get_value_linecol(doc["map"], "foo") == (2, 7)
        assert get_value_linecol(doc["map"], "bar") == (4, 10)
        assert get_value_linecol(doc["map"], "array") == (7, 4)
        assert get_value_linecol(doc["map"], "alias") == (8, 9)

    def test_array(self):
        doc = yaml_parser.load(
            textwrap.dedent(
                """
                array:
                  -   &anchor
                    Lorem ipsum dolor sit amet
                  -    consectetur adipiscing elit.
                  - *anchor
                  - map:
                      key: value
                """
            )
        )

        assert get_value_linecol(doc["array"], 0) == (2, 6)
        assert get_value_linecol(doc["array"], 1) == (4, 7)
        assert get_value_linecol(doc["array"], 2) is None
        assert get_value_linecol(doc["array"], 3) == (6, 4)
