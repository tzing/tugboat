import pydantic
from dirty_equals import AnyThing

from tests.dirty_equals import HasSubstring
from tugboat.constraints import accept_none, mutually_exclusive, require_all
from tugboat.types import Field


class SampleModel(pydantic.BaseModel):
    foo: str | None = None
    bar: str | None = pydantic.Field(None, alias="baz")


class TestAcceptNone:

    def test_pass(self):
        model = SampleModel(baz="baz")
        diagnoses = list(accept_none(model=model, loc=["spec"], fields=["foo"]))
        assert diagnoses == []

    def test_picked_1(self):
        model = SampleModel(baz="baz")
        diagnoses = list(
            accept_none(model=model, loc=["spec", 0, 1], fields=["foo", "bar"])
        )
        assert diagnoses == [
            {
                "type": "failure",
                "code": "M102",
                "loc": ("spec", 0, 1, "baz"),
                "summary": "Unexpected field 'baz'",
                "msg": "Field 'baz' is not allowed under @.spec[][]. Remove it.",
                "input": Field("baz"),
            }
        ]

    def test_picked_2(self):
        model = SampleModel(baz="baz")
        diagnoses = list(accept_none(model, fields=["foo", "bar"]))
        assert diagnoses == [
            {
                "type": "failure",
                "code": "M102",
                "loc": ("baz",),
                "summary": "Unexpected field 'baz'",
                "msg": "Field 'baz' is not allowed here. Remove it.",
                "input": Field("baz"),
            }
        ]


class TestMutuallyExclusive:

    def test_pass(self):
        model = SampleModel.model_validate({"baz": "baz"})
        diagnoses = list(
            mutually_exclusive(model=model, loc=["spec"], fields=["foo", "bar"])
        )
        assert diagnoses == []

    def test_none(self):
        model = SampleModel.model_validate({})
        diagnoses = list(
            mutually_exclusive(model=model, loc=["spec"], fields=["foo", "bar"])
        )
        assert diagnoses == []

    def test_require_one(self):
        model = SampleModel.model_validate({})
        diagnoses = list(
            mutually_exclusive(
                model, loc=["spec"], fields=["foo", "bar"], require_one=True
            )
        )
        assert diagnoses == [
            {
                "type": "failure",
                "code": "M101",
                "loc": ("spec",),
                "summary": "Missing required field",
                "msg": (
                    AnyThing()
                    & HasSubstring("Missing required field in @.spec.")
                    & HasSubstring("Set either one of these fields: 'baz' or 'foo'")
                ),
            }
        ]

    def test_too_many(self):
        model = SampleModel(foo="foo", baz="baz")
        diagnoses = list(
            mutually_exclusive(model=model, loc=["spec"], fields=["foo", "bar", "qux"])
        )
        assert diagnoses == [
            {
                "type": "failure",
                "code": "M201",
                "loc": ("spec", "foo"),
                "summary": "Conflicting fields",
                "msg": (
                    AnyThing()
                    & HasSubstring(
                        "Found multiple mutually exclusive fields set in @.spec."
                    )
                    & HasSubstring(
                        "These fields cannot be used at the same time: 'baz' and 'foo'"
                    )
                ),
                "input": Field("foo"),
            },
            {
                "type": "failure",
                "code": "M201",
                "loc": ("spec", "baz"),
                "summary": "Conflicting fields",
                "msg": (
                    AnyThing()
                    & HasSubstring(
                        "Found multiple mutually exclusive fields set in @.spec."
                    )
                    & HasSubstring(
                        "These fields cannot be used at the same time: 'baz' and 'foo'"
                    )
                ),
                "input": Field("baz"),
            },
        ]


class TestRequireAll:

    def test_pass(self):
        model = SampleModel(foo="foo", baz="baz")
        diagnoses = list(require_all(model=model, loc=["spec"], fields=["foo", "bar"]))
        assert diagnoses == []

    def test_strict(self):
        model = SampleModel(foo=None, baz="")
        diagnoses = list(require_all(model=model, loc=["spec"], fields=["foo", "bar"]))
        assert diagnoses == [
            {
                "type": "failure",
                "code": "M101",
                "loc": ("spec", "foo"),
                "summary": "Missing required field 'foo'",
                "msg": "Field 'foo' is required in the 'spec' section but missing.",
            },
            {
                "code": "M202",
                "loc": ("spec", "baz"),
                "msg": "Field 'baz' is required in the 'spec' section but is currently empty.",
                "summary": "Missing input in field 'baz'",
                "type": "failure",
            },
        ]

    def test_absent(self):
        model = SampleModel(foo=None, baz="")
        diagnoses = list(require_all(model, fields=["foo", "bar"], accept_empty=True))
        assert diagnoses == [
            {
                "type": "failure",
                "code": "M101",
                "loc": ("foo",),
                "summary": "Missing required field 'foo'",
                "msg": "Field 'foo' is required in current context but missing.",
            }
        ]
