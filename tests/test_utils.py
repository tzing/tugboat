import pytest

from tugboat.utils import get_context_name, join_items, prepend_loc


class TestPrependLoc:
    @pytest.fixture
    def diagnostics(self):
        return [
            {"loc": (), "code": "T01"},
            {"loc": ("foo",), "code": "T02"},
            {"loc": ("foo", "bar"), "code": "T03"},
        ]

    def test_standard(self, diagnostics):
        assert list(prepend_loc(["baz"], diagnostics)) == [
            {"loc": ("baz",), "code": "T01"},
            {"loc": ("baz", "foo"), "code": "T02"},
            {"loc": ("baz", "foo", "bar"), "code": "T03"},
        ]

    def test_empty(self, diagnostics):
        assert list(prepend_loc([], diagnostics)) == [
            {"loc": (), "code": "T01"},
            {"loc": ("foo",), "code": "T02"},
            {"loc": ("foo", "bar"), "code": "T03"},
        ]


class TestJoinItems:
    def test_single(self):
        assert join_items(["foo"]) == "'foo'"

    def test_two(self):
        assert join_items(["foo", "bar"], quote=False) == "foo and bar"

    def test_three(self):
        assert (
            join_items(["foo", "bar", "baz"], conjunction="or")
            == "'foo', 'bar' or 'baz'"
        )


class TestGetContextName:

    def test(self):
        assert get_context_name(["foo"]) == "the 'foo' section"
        assert get_context_name(("foo", 0, 1)) == "the 'foo' section"
        assert get_context_name(("foo", 0, 1, "bar")) == "the 'bar' section"
        assert get_context_name(()) == "current context"
