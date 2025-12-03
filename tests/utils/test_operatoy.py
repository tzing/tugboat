import pytest

from tugboat.schemas import Parameter
from tugboat.utils.operator import find_duplicate_names, prepend_loc


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

    def test_empty_items(self):
        assert list(prepend_loc(["foo"], [])) == []

    def test_empty_prefix(self, diagnoses):
        assert list(prepend_loc([], diagnoses)) == [
            {"loc": (), "code": "T01"},
            {"loc": ("foo",), "code": "T02"},
            {"loc": ("foo", "bar"), "code": "T03"},
        ]

    def test_from_iterables(self, diagnoses):
        def _generator():
            yield diagnoses

        assert list(prepend_loc.from_iterables(["baz"], _generator())) == [
            {"loc": ("baz",), "code": "T01"},
            {"loc": ("baz", "foo"), "code": "T02"},
            {"loc": ("baz", "foo", "bar"), "code": "T03"},
        ]


class TestFindDuplicateNames:

    def test_pass(self):
        items = [Parameter(name="name-1"), Parameter(name="name-2")]
        assert list(find_duplicate_names(items)) == []

    def test_picked(self):
        items = [
            Parameter(name="name-1"),
            Parameter(name="name-2"),
            Parameter(name="name-1"),
        ]
        assert list(find_duplicate_names(items)) == [(0, "name-1"), (2, "name-1")]
