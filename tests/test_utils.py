import pytest

from tugboat.utils import LruDict, get_context_name, join_items, prepend_loc


class TestPrependLoc:
    @pytest.fixture
    def diagnoses(self):
        return [
            {"loc": (), "code": "T01"},
            {"loc": ("foo",), "code": "T02"},
            {"loc": ("foo", "bar"), "code": "T03"},
        ]

    def test_standard(self, diagnoses):
        assert list(prepend_loc(["baz"], diagnoses)) == [
            {"loc": ("baz",), "code": "T01"},
            {"loc": ("baz", "foo"), "code": "T02"},
            {"loc": ("baz", "foo", "bar"), "code": "T03"},
        ]

    def test_empty(self, diagnoses):
        assert list(prepend_loc([], diagnoses)) == [
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


class TestLruDict:
    def test_basic(self):
        d = LruDict(max_size=3)
        d["a"] = 1
        d["b"] = 2
        d["c"] = 3
        assert d == {"a": 1, "b": 2, "c": 3}

    def test_exceed_max_size(self):
        d = LruDict(max_size=3)
        d["a"] = 1
        d["b"] = 2
        d["c"] = 3
        d["d"] = 4
        assert d == {"b": 2, "c": 3, "d": 4}

    def test_update(self):
        d = LruDict(max_size=3)
        d["a"] = 1
        d["b"] = 2
        d["c"] = 3
        d["b"] = 4
        assert list(d.items()) == [
            ("a", 1),
            ("c", 3),
            ("b", 4),
        ]

    def test_get(self):
        d = LruDict(max_size=3)
        d["a"] = 1
        d["b"] = 2
        d["c"] = 3
        assert d.get("a") == 1
        assert d.get("not-exists") is None
        assert list(d.items()) == [
            ("b", 2),
            ("c", 3),
            ("a", 1),
        ]

    def test_del(self):
        d = LruDict(max_size=3)
        d["a"] = 1
        d["b"] = 2
        d["c"] = 3
        del d["b"]
        assert d == {"a": 1, "c": 3}
