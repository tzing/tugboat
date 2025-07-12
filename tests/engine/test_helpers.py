import textwrap

import pytest
import ruamel.yaml
from ruamel.yaml.comments import CommentedBase

from tugboat.engine.helpers import (
    get_line_column,
    get_suppression_codes,
    parse_noqa_codes,
)
from tugboat.types import Field


@pytest.fixture()
def parser() -> ruamel.yaml.YAML:
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    return yaml


class TestGetLineColumn:

    @pytest.fixture(scope="class")
    def document(self, parser: ruamel.yaml.YAML) -> CommentedBase:
        return parser.load(
            textwrap.dedent(
                """
                spec:
                  name:  sample
                  items:
                    - string: test
                    - count:  5
                    - boolean: true
                    - map:
                        key: count
                        value:  1234
                """
            )
        )

    def test_name(self, document):
        loc = ("spec", "name")
        assert get_line_column(document, loc, Field("name")) == (2, 2)
        assert get_line_column(document, loc, "sample") == (2, 9)

    def test_items_0(self, document):
        loc = ("spec", "items", 0)
        assert get_line_column(document, loc, None) == (4, 6)

        loc = ("spec", "items", 0, "string")
        assert get_line_column(document, loc, Field("string")) == (4, 6)
        assert get_line_column(document, loc, "test") == (4, 14)

    def test_items_1(self, document):
        loc = ("spec", "items", 1)
        assert get_line_column(document, loc, None) == (5, 6)

        loc = ("spec", "items", 1, "count")
        assert get_line_column(document, loc, Field("count")) == (5, 6)
        assert get_line_column(document, loc, 5) == (5, 14)

    def test_items_2(self, document):
        loc = ("spec", "items", 2)
        assert get_line_column(document, loc, None) == (6, 6)

        loc = ("spec", "items", 2, "boolean")
        assert get_line_column(document, loc, Field("boolean")) == (6, 6)
        assert get_line_column(document, loc, True) == (6, 15)

    def test_items_3(self, document):
        loc = ("spec", "items", 3)
        assert get_line_column(document, loc, None) == (7, 6)

        loc = ("spec", "items", 3, "map")
        assert get_line_column(document, loc, Field("map")) == (7, 6)

        loc = ("spec", "items", 3, "map", "key")
        assert get_line_column(document, loc, Field("key")) == (8, 8)
        assert get_line_column(document, loc, "count") == (8, 13)

        loc = ("spec", "items", 3, "map", "value")
        assert get_line_column(document, loc, Field("value")) == (9, 8)
        assert get_line_column(document, loc, 1234) == (9, 16)

    def test_fallback(self, document):
        loc = ("spec", "nonexistent")
        assert get_line_column(document, loc, None) == (2, 2)
        assert get_line_column(document, loc, "nonexistent") == (2, 2)
        assert get_line_column(document, loc, Field("nonexistent")) == (2, 2)

        loc = ("spec", "items", 4)
        assert get_line_column(document, loc, None) == (4, 4)

    def test_basic(self, parser: ruamel.yaml.YAML):
        document = parser.load(
            textwrap.dedent(
                """
                foo:  Lorem ipsum dolor sit amet

                baz:
                  Lorem ipsum dolor sit amet,
                  consectetur adipiscing elit.

                qux: &qux Lorem ipsum dolor sit amet
                """
            )
        )

        loc = ("foo",)
        assert get_line_column(document, loc, Field("foo")) == (1, 0)
        assert get_line_column(document, loc, "ipsum") == (1, 12)

        loc = ("baz",)
        assert get_line_column(document, loc, Field("baz")) == (3, 0)
        assert get_line_column(document, loc, "ipsum") == (4, 2)

        loc = ("qux",)
        assert get_line_column(document, loc, Field("qux")) == (7, 0)
        assert get_line_column(document, loc, "ipsum") == (7, 5)

    def test_quoted(self, parser: ruamel.yaml.YAML):
        document = parser.load(
            textwrap.dedent(
                """
                foo:  "Lorem ipsum dolor sit amet"
                bar: 'consectetur adipiscing elit'

                baz:
                  "Lorem ipsum dolor sit amet,
                    consectetur adipiscing elit."

                qux: &qux "Lorem ipsum dolor sit amet"
                """
            )
        )

        loc = ("foo",)
        assert get_line_column(document, loc, Field("foo")) == (1, 0)
        assert get_line_column(document, loc, "ipsum") == (1, 13)

        loc = ("bar",)
        assert get_line_column(document, loc, Field("bar")) == (2, 0)
        assert get_line_column(document, loc, "adipiscing") == (2, 18)

        loc = ("baz",)
        assert get_line_column(document, loc, Field("baz")) == (4, 0)
        assert get_line_column(document, loc, "ipsum") == (5, 2)

        loc = ("qux",)
        assert get_line_column(document, loc, Field("qux")) == (8, 0)
        assert get_line_column(document, loc, "ipsum") == (8, 5)

    def test_literal(self, parser: ruamel.yaml.YAML):
        document = parser.load(
            textwrap.dedent(
                """
                foo: &foo |-
                  Lorem ipsum dolor sit amet,
                  consectetur adipiscing elit.

                bar: |-
                  Lorem ipsum dolor sit amet,
                  consectetur adipiscing elit.

                nested:
                    baz: |-
                        Lorem ipsum dolor sit amet,
                        consectetur adipiscing elit.
                """
            )
        )

        loc = ("foo",)
        assert get_line_column(document, loc, Field("foo")) == (1, 0)
        assert get_line_column(document, loc, "ipsum") == (2, 8)
        assert get_line_column(document, loc, "adipiscing") == (3, 14)

        loc = ("bar",)
        assert get_line_column(document, loc, Field("bar")) == (5, 0)
        assert get_line_column(document, loc, "ipsum") == (6, 8)
        assert get_line_column(document, loc, "adipiscing") == (7, 14)

        loc = ("nested", "baz")
        assert get_line_column(document, loc, Field("baz")) == (10, 4)
        assert get_line_column(document, loc, "ipsum") == (11, 14)
        assert get_line_column(document, loc, "adipiscing") == (12, 20)

    def test_folded(self, parser: ruamel.yaml.YAML):
        document = parser.load(
            textwrap.dedent(
                """
                foo:  >-
                  Lorem ipsum dolor sit amet,
                  consectetur adipiscing elit.

                bar: &bar >-
                  Lorem ipsum dolor sit amet,
                  consectetur adipiscing elit.
                """
            )
        )

        loc = ("foo",)
        assert get_line_column(document, loc, Field("foo")) == (1, 0)
        assert get_line_column(document, loc, "ipsum") == (1, 6)

        loc = ("bar",)
        assert get_line_column(document, loc, Field("bar")) == (5, 0)
        assert get_line_column(document, loc, "ipsum") == (5, 5)

    def test_anchor(self, parser: ruamel.yaml.YAML):
        document = parser.load(
            textwrap.dedent(
                """
                foo:  &foo Lorem ipsum dolor sit amet
                bar: *foo
                """
            )
        )

        loc = ("foo",)
        assert get_line_column(document, loc, "ipsum") == (1, 6)

        loc = ("bar",)
        assert get_line_column(document, loc, "ipsum") == (2, 5)


class TestGetSuppressionCodes:

    def test_1(self, parser: ruamel.yaml.YAML):
        doc = parser.load(
            """
            spec:
              name: sample # noqa: T01
              task: some task # noqa: T03
              items: # should not parsed noqa: T999
                - foo
                - name: bar # noqa: T04
                  type: string
            """
        )

        assert set(get_suppression_codes(doc, ("spec", "name"))) == {"T01"}
        assert set(get_suppression_codes(doc, ("spec", "task"))) == {"T03"}
        assert set(get_suppression_codes(doc, ("spec", "items", 1, "name"))) == {"T04"}

        assert not any(get_suppression_codes(doc, ("spec",)))
        assert not any(get_suppression_codes(doc, ("spec", "items", 0)))

    def test_2(self, parser: ruamel.yaml.YAML):
        document = parser.load(
            """
            spec: # noqa
              name: sample
            """
        )
        assert "ANYTHING" in get_suppression_codes(document, ("spec", "name"))

    def test_3(self, parser: ruamel.yaml.YAML):
        document = parser.load(
            """
            spec:
              name:
                # noqa: T01
                test case

              desc: | # noqa: T02
                Lorem ipsum dolor sit amet,
                consectetur adipiscing elit.
            """
        )
        assert set(get_suppression_codes(document, ("spec", "name"))) == {"T01"}
        assert set(get_suppression_codes(document, ("spec", "desc"))) == {"T02"}

    def test_fallback(self, parser: ruamel.yaml.YAML):
        document = parser.load(
            """
            spec: # noqa: T01
              name: sample
            """
        )
        codes = get_suppression_codes(document, ("spec", "no-this-field"))
        assert set(codes) == {"T01"}


class TestParseNoqaCodes:

    @pytest.mark.parametrize(
        ("comment", "expected"),
        [
            ("# some comments follows by noqa: T01", []),
            ("#noqa: T01", ["T01"]),
            ("# NOQA:t01,t02", ["T01", "T02"]),
            ("# noqa: T01, T02, T03", ["T01", "T02", "T03"]),
            ("# noqa: T01, T02, T03; comment", ["T01", "T02", "T03"]),
            ("# noqa: T01, T02, T03; comment, QAX", ["T01", "T02", "T03"]),
        ],
    )
    def test_basic(self, comment: str, expected: list[str]):
        codes = list(parse_noqa_codes(comment))
        assert codes == expected

    def test_empty(self):
        assert list(parse_noqa_codes("")) == []

    def test_all(self):
        assert "T999" in parse_noqa_codes("#noqa")
