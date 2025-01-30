import pytest
from pydantic import BaseModel

from tugboat.references.context import ReferenceCollection
from tugboat.schemas import Parameter
from tugboat.utils.operator import (
    check_model_fields_references,
    find_duplicate_names,
    prepend_loc,
)


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


class TestCheckModelFieldsReferences:

    def test_picked(self):
        class Nested(BaseModel):
            foo: str

        class Model(BaseModel):
            bar: list[Nested]
            baz: str
            qax: int
            qux: Nested

        model = Model.model_validate(
            {
                "baz": "leorm",
                "qax": 42,
                "qux": {"foo": "{{ error"},
                "bar": [
                    {"foo": "bar"},
                    {"foo": "{{ valid }}"},
                    {"foo": "{{ invalid }}"},
                ],
            }
        )

        refs = ReferenceCollection()
        refs.add(("valid",))

        assert list(check_model_fields_references(model, refs)) == [
            {
                "code": "VAR002",
                "fix": "{{ valid }}",
                "input": "{{ invalid }}",
                "loc": ("bar", 2, "foo"),
                "msg": "The used reference 'invalid' is invalid.",
                "summary": "Invalid reference",
                "ctx": {
                    "closest": ("valid",),
                    "ref": ("invalid",),
                },
            },
            {
                "code": "VAR001",
                "input": "{{ error",
                "loc": ("qux", "foo"),
                "msg": "Invalid syntax near '{{ error': expect closing tag '}}'",
                "summary": "Syntax error",
            },
        ]
