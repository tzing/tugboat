from __future__ import annotations

from pydantic import BaseModel

from tugboat.analyzers.generic import check_argo_variable_errors, report_duplicate_names
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


class TestCheckArgoVariableErrors:

    def test_pass(self):
        class Model(BaseModel):
            field1: str = "value"
            field2: int = 1234

        assert list(check_argo_variable_errors(Model(), ReferenceCollection())) == []

    def test_picked(self):
        class Nested(BaseModel):
            field1: int = 1234
            field2: str = "{{ invalid }}"

        class Model(BaseModel):
            array: list[Nested]

        model = Model(array=[Nested()])

        assert list(check_argo_variable_errors(model, ReferenceCollection())) == [
            {
                "code": "VAR002",
                "loc": ("array", 0, "field2"),
                "summary": "Invalid reference",
                "msg": "The used reference 'invalid' is invalid.",
                "input": "{{ invalid }}",
                "fix": None,
            }
        ]
