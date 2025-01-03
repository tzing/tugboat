from __future__ import annotations

from tugboat.analyzers.generic import report_duplicate_names
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
