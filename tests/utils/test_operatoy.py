import pytest

from tugboat.utils.operator import prepend_loc


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
