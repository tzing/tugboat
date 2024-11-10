from unittest.mock import Mock

from pydantic import BaseModel

from tests.utils import ContainsSubStrings
from tugboat.constraints import (
    accept_none,
    mutually_exclusive,
    require_all,
    require_exactly_one,
)


class TestAcceptNone:

    def test_pass(self):
        model = Mock(BaseModel, foo=None, bar="bar")
        diagnostics = list(accept_none(model=model, loc=["spec"], fields=["foo"]))
        assert diagnostics == []

    def test_picked_1(self):
        model = Mock(BaseModel, foo=None, bar="bar")
        diagnostics = list(
            accept_none(model=model, loc=["spec", 0, 1, "baz"], fields=["foo", "bar"])
        )
        assert diagnostics == [
            {
                "type": "failure",
                "code": "M005",
                "loc": ("spec", 0, 1, "baz", "bar"),
                "summary": "Found redundant field 'bar'",
                "msg": "Field 'bar' is not valid within the 'baz' section.",
                "input": "bar",
            }
        ]

    def test_picked_2(self):
        model = Mock(BaseModel, foo=None, bar="bar")
        diagnostics = list(
            accept_none(model=model, loc=["spec", 0, 1], fields=["foo", "bar"])
        )
        assert diagnostics == [
            {
                "type": "failure",
                "code": "M005",
                "loc": ("spec", 0, 1, "bar"),
                "summary": "Found redundant field 'bar'",
                "msg": "Field 'bar' is not valid within the 'spec' section.",
                "input": "bar",
            }
        ]


class TestMutuallyExclusive:

    def test_pass(self):
        model = Mock(BaseModel, foo=None, bar="bar")
        diagnostics = list(
            mutually_exclusive(model=model, loc=["spec"], fields=["foo", "bar"])
        )
        assert diagnostics == []

    def test_none(self):
        model = Mock(BaseModel, foo=None, bar=None)
        diagnostics = list(
            mutually_exclusive(model=model, loc=["spec"], fields=["foo", "bar"])
        )
        assert diagnostics == []

    def test_too_many(self):
        model = Mock(BaseModel, foo="foo", bar="bar")
        diagnostics = list(
            mutually_exclusive(model=model, loc=["spec"], fields=["foo", "bar"])
        )
        assert diagnostics == [
            {
                "type": "failure",
                "code": "M006",
                "loc": ("spec", "foo"),
                "summary": "Mutually exclusive field set",
                "msg": "Field 'foo' and 'bar' are mutually exclusive.",
                "input": "foo",
            },
            {
                "type": "failure",
                "code": "M006",
                "loc": ("spec", "bar"),
                "summary": "Mutually exclusive field set",
                "msg": "Field 'foo' and 'bar' are mutually exclusive.",
                "input": "bar",
            },
        ]


class TestRequireAll:

    def test_pass(self):
        model = Mock(BaseModel, foo="foo", bar="bar")
        diagnostics = list(
            require_all(model=model, loc=["spec"], fields=["foo", "bar"])
        )
        assert diagnostics == []

    def test_missing(self):
        model = Mock(BaseModel, foo=None, bar="")
        diagnostics = list(
            require_all(model=model, loc=["spec"], fields=["foo", "bar"])
        )
        assert diagnostics == [
            {
                "type": "failure",
                "code": "M004",
                "loc": ("spec", "foo"),
                "summary": "Missing required field 'foo'",
                "msg": "Field 'foo' is required in the 'spec' section but missing",
            },
            {
                "type": "failure",
                "code": "M004",
                "loc": ("spec", "bar"),
                "summary": "Missing required field 'bar'",
                "msg": "Field 'bar' is required in the 'spec' section but empty",
            },
        ]


class TestRequireExactlyOne:

    def test_pass(self):
        model = Mock(BaseModel, foo=None, bar="bar")
        diagnostics = list(
            require_exactly_one(model=model, loc=["spec"], fields=["foo", "bar"])
        )
        assert diagnostics == []

    def test_missing(self):
        model = Mock(BaseModel, foo=None, bar=None)
        diagnostics = list(
            require_exactly_one(model=model, loc=["spec"], fields=["foo", "bar"])
        )
        assert diagnostics == [
            {
                "type": "failure",
                "code": "M004",
                "loc": ("spec",),
                "summary": "Missing required field",
                "msg": ContainsSubStrings(
                    "Missing required field for the 'spec' section.",
                    "One of the following fields is required: 'foo' or 'bar'.",
                ),
            }
        ]

    def test_too_many(self):
        model = Mock(BaseModel, foo="foo", bar="bar")
        diagnostics = list(
            require_exactly_one(model=model, loc=["spec"], fields=["foo", "bar"])
        )
        assert diagnostics == [
            {
                "type": "failure",
                "code": "M006",
                "loc": ("spec", "foo"),
                "summary": "Mutually exclusive field set",
                "msg": "Field 'foo' and 'bar' are mutually exclusive.",
                "input": "foo",
            },
            {
                "type": "failure",
                "code": "M006",
                "loc": ("spec", "bar"),
                "summary": "Mutually exclusive field set",
                "msg": "Field 'foo' and 'bar' are mutually exclusive.",
                "input": "bar",
            },
        ]
