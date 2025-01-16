from unittest.mock import Mock

import pytest
from pydantic import BaseModel, Field, ValidationError

from tests.utils import ContainsSubStrings
from tugboat.constraints import (
    accept_none,
    get_alias,
    mutually_exclusive,
    require_all,
    require_exactly_one,
)


class SampleModel(BaseModel):
    foo: str | None = None
    bar: str | None = Field(None, alias="baz")


class TestAcceptNone:

    def test_pass(self):
        model = SampleModel(baz="baz")
        diagnoses = list(accept_none(model=model, loc=["spec"], fields=["foo"]))
        assert diagnoses == []

    def test_picked_1(self):
        model = SampleModel(baz="baz")
        diagnoses = list(
            accept_none(model=model, loc=["spec", 0, 1, "baz"], fields=["foo", "bar"])
        )
        assert diagnoses == [
            {
                "type": "failure",
                "code": "M005",
                "loc": ("spec", 0, 1, "baz", "baz"),
                "summary": "Found redundant field 'baz'",
                "msg": "Field 'baz' is not valid within the 'baz' section.",
                "input": "baz",
            }
        ]

    def test_picked_2(self):
        model = SampleModel(baz="baz")
        diagnoses = list(
            accept_none(model=model, loc=["spec", 0, 1], fields=["foo", "bar"])
        )
        assert diagnoses == [
            {
                "type": "failure",
                "code": "M005",
                "loc": ("spec", 0, 1, "baz"),
                "summary": "Found redundant field 'baz'",
                "msg": "Field 'baz' is not valid within the 'spec' section.",
                "input": "baz",
            }
        ]


class TestMutuallyExclusive:

    def test_pass(self):
        model = SampleModel(baz="baz")
        diagnoses = list(
            mutually_exclusive(model=model, loc=["spec"], fields=["foo", "bar"])
        )
        assert diagnoses == []

    def test_none(self):
        model = SampleModel()
        diagnoses = list(
            mutually_exclusive(model=model, loc=["spec"], fields=["foo", "bar"])
        )
        assert diagnoses == []

    def test_too_many(self):
        model = SampleModel(foo="foo", baz="baz")
        diagnoses = list(
            mutually_exclusive(model=model, loc=["spec"], fields=["foo", "bar"])
        )
        assert diagnoses == [
            {
                "type": "failure",
                "code": "M006",
                "loc": ("spec", "baz"),
                "summary": "Mutually exclusive field set",
                "msg": "Field 'baz' and 'foo' are mutually exclusive.",
                "input": "baz",
            },
            {
                "type": "failure",
                "code": "M006",
                "loc": ("spec", "foo"),
                "summary": "Mutually exclusive field set",
                "msg": "Field 'baz' and 'foo' are mutually exclusive.",
                "input": "foo",
            },
        ]


class TestRequireAll:

    def test_pass(self):
        model = SampleModel(foo="foo", baz="baz")
        diagnoses = list(require_all(model=model, loc=["spec"], fields=["foo", "bar"]))
        assert diagnoses == []

    def test_missing(self):
        model = SampleModel(foo=None, baz="")
        diagnoses = list(require_all(model=model, loc=["spec"], fields=["foo", "bar"]))
        assert diagnoses == [
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
                "loc": ("spec", "baz"),
                "summary": "Missing required field 'baz'",
                "msg": "Field 'baz' is required in the 'spec' section but empty",
            },
        ]


class TestRequireExactlyOne:

    def test_pass(self):
        model = Mock(BaseModel, foo=None, bar="bar")
        diagnoses = list(
            require_exactly_one(model=model, loc=["spec"], fields=["foo", "bar"])
        )
        assert diagnoses == []

    def test_missing(self):
        model = Mock(BaseModel, foo=None, bar=None)
        diagnoses = list(
            require_exactly_one(model=model, loc=["spec"], fields=["foo", "bar"])
        )
        assert diagnoses == [
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
        diagnoses = list(
            require_exactly_one(model=model, loc=["spec"], fields=["foo", "bar"])
        )
        assert diagnoses == [
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


class TestGetAlias:

    def test(self):
        class Model(BaseModel):
            x: str
            y: str = Field(alias="z")

        m = Model(x="hello", z="world")

        assert get_alias(m, "x") == "x"
        assert get_alias(m, "y") == "z"
