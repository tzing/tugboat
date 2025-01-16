from __future__ import annotations

from pydantic import BaseModel

from tugboat.analyzers.generic import (
    check_model_fields_references,
    report_duplicate_names,
)
from tugboat.references.context import ReferenceCollection
from tugboat.schemas import Parameter


class TestReportDuplicateNames:

    def test_pass(self):
        items = [Parameter(name="name-1"), Parameter(name="name-2")]
        assert list(report_duplicate_names(items)) == []

    def test_picked(self):
        items = [
            Parameter(name="name-1"),
            Parameter(name="name-2"),
            Parameter(name="name-1"),
        ]
        assert list(report_duplicate_names(items)) == [(0, "name-1"), (2, "name-1")]


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
                "ctx": {
                    "closest": ("valid",),
                    "ref": ("invalid",),
                },
                "fix": "{{ valid }}",
                "input": "{{ invalid }}",
                "loc": ("bar", 2, "foo"),
                "msg": "The used reference 'invalid' is invalid.",
                "summary": "Invalid reference",
            },
            {
                "code": "VAR001",
                "input": "{{ error",
                "loc": ("qux", "foo"),
                "msg": "Invalid syntax near '{{ error': expect closing tag '}}'",
                "summary": "Syntax error",
            },
        ]
