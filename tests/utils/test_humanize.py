
from tugboat.utils.humanize import (
    get_context_name,
    join,
    join_with_and,
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

    def test_join_with_and(self):
        assert join_with_and(["foo"]) == "'foo'"
        assert join_with_and(["foo", "bar"], quote=False) == "bar and foo"
        assert join_with_and(["foo", "bar"], sort=False) == "'foo' and 'bar'"
        assert join_with_and([]) == "(none)"

    def test_join_with_or(self):
        assert join_with_or(["foo"]) == "'foo'"
        assert join_with_or(["foo", "bar"], quote=False) == "bar or foo"
        assert join_with_or(["foo", "bar"], sort=False) == "'foo' or 'bar'"
        assert join_with_or([]) == "(none)"


class TestGetContextName:

    def test(self):
        assert get_context_name(["foo"]) == "the 'foo' section"
        assert get_context_name(("foo", 0, 1)) == "the 'foo' section"
        assert get_context_name(("foo", 0, 1, "bar")) == "the 'bar' section"
        assert get_context_name(()) == "current context"
