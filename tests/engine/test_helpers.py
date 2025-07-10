import textwrap

import pytest
import ruamel.yaml

from tugboat.engine.helpers import get_line_column
from tugboat.types import Field


class TestGetLineColumn:

    @pytest.fixture(scope="class")
    def document(self):
        yaml = ruamel.yaml.YAML()
        yaml.preserve_quotes = True
        return yaml.load(
            textwrap.dedent(
                """
                spec:
                  name: &anchor sample

                  description: |-
                    This is a sample description
                    that contains multiple lines.

                  is-task: true

                  steps:
                    - name: baz
                      data: 123

                  alias: *anchor
                """
            )
        )

    def test_name(self, document):
        loc = ("spec", "name")
        assert get_line_column(document, loc, Field("name")) == (2, 2)
        assert get_line_column(document, loc, "sample") == (2, 16)

    def test_description(self, document):
        loc = ("spec", "description")
        assert get_line_column(document, loc, Field("description")) == (4, 2)
        assert get_line_column(document, loc, "description") == (5, 21)
        assert get_line_column(document, loc, "multiple") == (6, 18)
        assert get_line_column(document, loc, "no-this-text") == (4, 15)

    def test_is_task(self, document):
        loc = ("spec", "is-task")
        assert get_line_column(document, loc, Field("is-task")) == (8, 2)
        assert get_line_column(document, loc, True) == (8, 11)

    def test_steps(self, document):
        loc = ("spec", "steps", 0, "name")
        assert get_line_column(document, loc, Field("name")) == (11, 6)
        assert get_line_column(document, loc, "az") == (11, 13)

        loc = ("spec", "steps", 0, "data")
        assert get_line_column(document, loc, Field("data")) == (12, 6)
        assert get_line_column(document, loc, 123) == (12, 12)

    def test_alias(self, document):
        loc = ("spec", "alias")
        assert get_line_column(document, loc, Field("alias")) == (14, 2)
        assert get_line_column(document, loc, "sample") == (14, 9)

    def test_fallback(self, document):
        loc = ("spec", "nonexistent")
        assert get_line_column(document, loc, "nonexistent") == (2, 2)
        assert get_line_column(document, loc, Field("nonexistent")) == (2, 2)
