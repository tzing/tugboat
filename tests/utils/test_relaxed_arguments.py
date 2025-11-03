import datetime

from dirty_equals import IsPartialDict

from tests.dirty_equals import ContainsSubStrings
from tugboat.schemas.arguments import RelaxedParameter
from tugboat.utils.relaxed_arguments import (
    critique_relaxed_parameter,
)


class TestCritiqueRelaxedParameter:

    def test_1(self):
        param = RelaxedParameter.model_validate(
            {
                "name": "test",
                "value": {"key": "value"},
            }
        )
        assert list(critique_relaxed_parameter(param)) == [
            {
                "type": "failure",
                "code": "M103",
                "loc": ("value",),
                "summary": "Input type mismatch",
                "msg": ContainsSubStrings(
                    "Expected string for parameter value, but received a mapping.",
                    "If you want to pass an object, try serializing it to a JSON string.",
                ),
                "input": {"key": "value"},
                "fix": '{\n  "key": "value"\n}',
            }
        ]

    def test_2(self):
        param = RelaxedParameter.model_validate(
            {
                "name": "test",
                "value": [],
            }
        )
        assert list(critique_relaxed_parameter(param)) == [
            {
                "type": "failure",
                "code": "M103",
                "loc": ("value",),
                "summary": "Input type mismatch",
                "msg": ContainsSubStrings(
                    "Expected string for parameter value, but received a array.",
                    "If you want to pass an object, try serializing it to a JSON string.",
                ),
                "input": [],
                "fix": '"[]"',
            }
        ]

    def test_json_error(self):
        param = RelaxedParameter.model_validate(
            {
                "name": "test",
                "value": {
                    "key": datetime.datetime.now()  # will cause a serialization error
                },
            }
        )
        assert list(critique_relaxed_parameter(param)) == [
            IsPartialDict(
                {
                    "type": "failure",
                    "code": "M103",
                    "loc": ("value",),
                    "summary": "Input type mismatch",
                    "msg": ContainsSubStrings(
                        "Expected string for parameter value, but received a mapping.",
                        "If you want to pass an object, try serializing it to a JSON string.",
                    ),
                }
            )
        ]

    def test_non_object(self):
        param = RelaxedParameter.model_validate(
            {
                "name": "test",
                "value": 3.14,
            }
        )
        assert list(critique_relaxed_parameter(param)) == [
            {
                "type": "failure",
                "code": "M103",
                "loc": ("value",),
                "summary": "Input type mismatch",
                "msg": "Expected string for parameter value, but received a number.",
                "input": 3.14,
            }
        ]
