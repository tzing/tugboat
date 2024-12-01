import copy

import pytest

from tugboat.references.cache import LruDict
from tugboat.references.context import AnyStr, Context, ReferenceCollection


class TestReferenceCollection:

    def test(self):
        collection = ReferenceCollection()
        assert len(collection) == 0

        collection |= {
            ("a", "b"),
            ("c", AnyStr),
        }
        assert len(collection) == 2

        assert ("a", "b") in collection
        assert ("c", "SOMETHING-ELSE") in collection

        assert repr(collection) == "{('a', 'b'), ('c', ANY)}"

    def test_errors(self):
        collection = ReferenceCollection()
        with pytest.raises(TypeError):
            collection.add("not-a-tuple")
        with pytest.raises(NotImplementedError):
            collection.discard(("a", "b"))

    @pytest.mark.parametrize(
        ("target", "expected"),
        [
            # exact match
            (("red", "pink"), ("red", "pink")),
            (("red", "teal", "pink"), ("red", "teal", "pink")),
            # length mismatch
            (("red", "pink", "EXTRA"), ("red", "pink")),
            (("green",), ("green", "yellow")),
            # character mismatch
            (("red", "pinkk"), ("red", "pink")),
            (("red", "teel", "pink"), ("red", "teal", "pink")),
            # match `AnyStr`
            (("green", "grey", "WHATEVER"), ("green", "grey", "WHATEVER")),
            (("green", "grey", "WHATEVER", "SUB"), ("green", "grey", "WHATEVER")),
            (("green", "grey"), ("green", "yellow")),
        ],
    )
    def test_find_closest(self, target, expected):
        collection = ReferenceCollection()
        collection |= {
            ("red", "blue"),
            ("red", "pink"),
            ("red", "blue", "pink"),
            ("red", "teal", "pink"),
            ("red", "blue", "pink", "gray"),
            ("red", "blue", "teal", "gray"),
            ("green", "yellow"),
            ("green", "grey", AnyStr),
        }
        assert collection.find_closest(target) == expected

    def test_empty(self):
        collection = ReferenceCollection()
        assert collection.find_closest(("foo", "bar")) == ()
        assert collection.find_closest(()) == ()


class TestContext:

    def test_copy(self):
        ctx_1 = Context()
        ctx_2 = copy.deepcopy(ctx_1)

        ctx_1.parameters.add(("a", "b"))
        ctx_2.parameters.add(("foo", "bar"))

        assert ("a", "b") in ctx_1.parameters
        assert ("a", "b") not in ctx_2.parameters

        assert ("foo", "bar") in ctx_2.parameters
        assert ("foo", "bar") not in ctx_1.parameters


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
