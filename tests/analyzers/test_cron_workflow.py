from tests.dirty_equals import ContainsSubStrings, IsPartialModel
from tugboat.engine import analyze_yaml_stream


class TestRules:

    def test_name_too_long_1(self, diagnoses_logger):
        diagnoses = analyze_yaml_stream(MANIFEST_NAME_TOO_LONG)
        diagnoses_logger(diagnoses)
        assert (
            IsPartialModel(
                {
                    "code": "CW001",
                    "loc": ("metadata", "name"),
                    "msg": ContainsSubStrings(
                        "The maximum length of a CronWorkflow name is 52 characters."
                    ),
                }
            )
            in diagnoses
        )

    def test_name_too_long_2(self, diagnoses_logger):
        diagnoses = analyze_yaml_stream(MANIFEST_GENERATE_NAME_TOO_LONG)
        diagnoses_logger(diagnoses)
        assert (
            IsPartialModel(
                {
                    "code": "CW001",
                    "loc": ("metadata", "generateName"),
                    "msg": ContainsSubStrings(
                        "The maximum length of a CronWorkflow generate name is 47 characters."
                    ),
                }
            )
            in diagnoses
        )


MANIFEST_NAME_TOO_LONG = """
apiVersion: argoproj.io/v1alpha1
kind: CronWorkflow
metadata:
  name: a-very-long-name-that-exceeds-the-maximum-length-of-52-characters
spec:
  schedule: "* * * * *"
  concurrencyPolicy: "Replace"
  startingDeadlineSeconds: 0
  workflowSpec:
    entrypoint: date
    templates:
    - name: date
      container:
        image: alpine:3.6
        command: [sh, -c]
        args: ["date; sleep 90"]
"""


MANIFEST_GENERATE_NAME_TOO_LONG = """
apiVersion: argoproj.io/v1alpha1
kind: CronWorkflow
metadata:
  generateName: a-very-long-name-that-exceeds-the-maximum-length-of-52-characters
spec:
  schedule: "* * * * *"
  concurrencyPolicy: "Replace"
  startingDeadlineSeconds: 0
  workflowSpec:
    entrypoint: date
    templates:
    - name: date
      container:
        image: alpine:3.6
        command: [sh, -c]
        args: ["date; sleep 90"]
"""
