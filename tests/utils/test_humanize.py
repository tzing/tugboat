from pydantic import BaseModel, Field

from tugboat.utils.humanize import (
    get_alias,
    get_context_name,
    join_with_and,
    join,
    join_with_or,
)


class TestJoin:

    def test_1(self):
        assert join(["foo"]) == "foo"
        assert join(["foo", "bar"]) == "foo, bar"
        assert join(["foo", "bar", "baz"]) == "foo, bar, baz"

    def test_2(self):
        assert join(["foo"], last_joiner=", and ") == "foo"
        assert join(["foo", "bar"], last_joiner=", and ") == "foo, and bar"
        assert join(["foo", "bar", "baz"], last_joiner=", and ") == "foo, bar, and baz"

    def test_empty(self):
        assert join([]) == ""


class TestJoinItems:
    def test_single(self):
        assert join_with_and(["foo"]) == "'foo'"

    def test_two(self):
        assert join_with_and(["foo", "bar"], quote=False) == "foo and bar"

    def test_three(self):
        assert join_with_or(["foo", "bar", "baz"]) == "'foo', 'bar' or 'baz'"

    def test_empty(self):
        assert join_with_and([]) == "(none)"


class TestGetContextName:

    def test(self):
        assert get_context_name(["foo"]) == "the 'foo' section"
        assert get_context_name(("foo", 0, 1)) == "the 'foo' section"
        assert get_context_name(("foo", 0, 1, "bar")) == "the 'bar' section"
        assert get_context_name(()) == "current context"


class TestGetAlias:

    def test(self):
        class Model(BaseModel):
            x: str
            y: str = Field(alias="z")

        m = Model(x="hello", z="world")

        assert get_alias(m, "x") == "x"
        assert get_alias(m, "y") == "z"
