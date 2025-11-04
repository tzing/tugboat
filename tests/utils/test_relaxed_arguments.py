import datetime

from dirty_equals import IsPartialDict

from tests.dirty_equals import ContainsSubStrings
from tugboat.schemas.arguments import RelaxedArtifact, RelaxedParameter
from tugboat.utils.relaxed_arguments import (
    critique_relaxed_artifact,
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


class TestCritiqueRelaxedArtifact:

    def test_1(self):
        artifact = RelaxedArtifact.model_validate(
            {
                "name": "test",
                "value": 1234,
            }
        )
        assert list(critique_relaxed_artifact(artifact)) == [
            {
                "type": "failure",
                "code": "M102",
                "loc": ("value",),
                "summary": "Found redundant field",
                "msg": ContainsSubStrings(
                    "Field 'value' is not a valid field for artifact."
                ),
                "input": "value",
                "fix": 'raw:\n  data: "1234"',
            }
        ]

    def test_2(self):
        artifact = RelaxedArtifact.model_validate(
            {
                "name": "test",
                "value": {
                    "key": "value",
                },
            }
        )
        assert list(critique_relaxed_artifact(artifact)) == [
            IsPartialDict(
                {
                    "code": "M102",
                    "loc": ("value",),
                    "fix": "\n".join(
                        [
                            "raw:",
                            "  data: |-",
                            "    {",
                            '      "key": "value"',
                            "    }",
                        ]
                    ),
                }
            )
        ]

    def test_json_error(self):
        artifact = RelaxedArtifact.model_validate(
            {
                "name": "test",
                "value": {
                    "dt": datetime.date(2025, 3, 31),
                },
            }
        )
        assert list(critique_relaxed_artifact(artifact)) == [
            IsPartialDict(
                {
                    "code": "M102",
                    "loc": ("value",),
                    "fix": None,
                }
            )
        ]
