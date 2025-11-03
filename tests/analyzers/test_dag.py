import pytest

from tests.dirty_equals import ContainsSubStrings, IsPartialModel
from tugboat.engine import analyze_yaml_stream


def test_analyze_task(diagnoses_logger):
    diagnoses = analyze_yaml_stream(
        """
        apiVersion: argoproj.io/v1alpha1
        kind: Workflow
        metadata:
          generateName: test-
        spec:
          entrypoint: main
          templates:
            - name: main
              dag:
                tasks:
                  - name: task-2
                    depends: task-1
                    dependencies:
                      - task-1
                    template: test
                  - name: deprecated
                    onExit: exit
                    template: print-message
        """
    )
    diagnoses_logger(diagnoses)

    loc = ("spec", "templates", 0, "dag", "tasks", 0)
    assert IsPartialModel({"code": "M201", "loc": (*loc, "depends")}) in diagnoses
    assert IsPartialModel({"code": "M201", "loc": (*loc, "dependencies")}) in diagnoses


def test_check_argument_parameters(diagnoses_logger):
    diagnoses = analyze_yaml_stream(MANIFEST_INVALID_INPUT_PARAMETERS)
    diagnoses_logger(diagnoses)

    loc_prefix = ("spec", "templates", 0, "dag", "tasks", 0, "arguments", "parameters")

    # DAG102: Duplicate parameter name
    assert IsPartialModel(code="DAG102", loc=(*loc_prefix, 0, "name")) in diagnoses
    assert IsPartialModel(code="DAG102", loc=(*loc_prefix, 1, "name")) in diagnoses


MANIFEST_INVALID_INPUT_PARAMETERS = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  entrypoint: main
  templates:
    - name: main
      dag:
        tasks:
          - name: step1
            arguments:
              parameters:
                - name: param1
                  value: "value1"
                - name: param1
                  value: "value2"
"""


def test_check_argument_artifacts(diagnoses_logger):
    diagnoses = analyze_yaml_stream(MANIFEST_INVALID_INPUT_ARTIFACTS)
    diagnoses_logger(diagnoses)

    loc_prefix = ("spec", "templates", 0, "dag", "tasks", 0, "arguments", "artifacts")

    # DAG103: Duplicate artifact name
    assert IsPartialModel(code="DAG103", loc=(*loc_prefix, 0, "name")) in diagnoses
    assert IsPartialModel(code="DAG103", loc=(*loc_prefix, 1, "name")) in diagnoses


MANIFEST_INVALID_INPUT_ARTIFACTS = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  entrypoint: main
  templates:
    - name: main
      dag:
        tasks:
          - name: step1
            arguments:
              artifacts:
                - name: artifact1
                  from: "{{workflow.invalid}}"
                - name: artifact1
                  raw:
                    data: "some data"
"""


def test_check_referenced_template(caplog: pytest.LogCaptureFixture, diagnoses_logger):
    with caplog.at_level("DEBUG", "tugboat.analyzers.dag"):
        diagnoses = analyze_yaml_stream(
            """
            apiVersion: argoproj.io/v1alpha1
            kind: WorkflowTemplate
            metadata:
              name: demo
            spec:
              templates:
                - name: main
                  dag:
                    tasks:
                      - name: loop
                        template: main

                - name: invalid-reference
                  dag:
                    tasks:
                      - name: missing
                        templateRef:
                          name: demo
                          template: not-exist-template
                      - name: external
                        templateRef:
                          name: another-workflow
                          template: whatever

                - name: another
                  suspend: {}
            """
        )

    diagnoses_logger(diagnoses)

    assert (
        IsPartialModel(
            {
                "code": "DAG201",
                "loc": ("spec", "templates", 0, "dag", "tasks", 0, "template"),
            }
        )
        in diagnoses
    )
    assert (
        "Task 'external': Referenced template 'another-workflow' is not the same as current workflow 'demo'. Skipping."
        in caplog.text
    )
