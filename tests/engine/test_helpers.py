import textwrap

import pytest
import ruamel.yaml
from ruamel.yaml.comments import CommentedBase
from ruamel.yaml.error import MarkedYAMLError

from tests.dirty_equals import IsMatch, IsPartialModel
from tugboat.engine.helpers import (
    get_suppression_codes,
    parse_noqa_codes,
    translate_marked_yaml_error,
)
from tugboat.types import Field


@pytest.fixture
def parser() -> ruamel.yaml.YAML:
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    return yaml


class TestTranslateMarkedYamlError:

    def test(self, parser: ruamel.yaml.YAML):
        with pytest.raises(MarkedYAMLError) as exc_info:
            parser.load('test: "foo')

        assert translate_marked_yaml_error(exc_info.value) == IsPartialModel(
            line=1,
            column=11,
            type="error",
            code="F002",
            loc=(),
            summary="Malformed YAML document",
            msg=IsMatch(r"^found unexpected end of stream"),
        )


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
