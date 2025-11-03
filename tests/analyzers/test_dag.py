import pytest
from dirty_equals import AnyThing

from tests.dirty_equals import HasSubstring, IsPartialModel
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
    assert IsPartialModel(code="M201", loc=(*loc, "depends")) in diagnoses
    assert IsPartialModel(code="M201", loc=(*loc, "dependencies")) in diagnoses


def test_check_argument_parameters(diagnoses_logger):
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
                  - name: step1
                    arguments:
                      parameters:
                        - name: param1
                          value: "value1"
                        - name: param1
                          value: "value2"
        """
    )
    diagnoses_logger(diagnoses)

    loc_prefix = ("spec", "templates", 0, "dag", "tasks", 0, "arguments", "parameters")
    assert IsPartialModel(code="DAG102", loc=(*loc_prefix, 0, "name")) in diagnoses
    assert IsPartialModel(code="DAG102", loc=(*loc_prefix, 1, "name")) in diagnoses


def test_check_argument_parameter_fields(diagnoses_logger):
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
                  - name: task1
                    template: compute
                    arguments:
                      parameters:
                        - name: message
                          valueFrom:
                            path: /tmp/message
                        - name: invalid-ref
                          value: "{{ workflow.invalid }}"
                        - name: structured
                          value:
                            foo: bar
                        - name: ""
                          value: foo
                        - name: both
                          value: baz
                          valueFrom:
                            parameter: message
            - name: compute
              container:
                image: alpine:3.19
        """
    )
    diagnoses_logger(diagnoses)

    loc_prefix = ("spec", "templates", 0, "dag", "tasks", 0, "arguments", "parameters")
    assert (
        IsPartialModel(code="M102", loc=(*loc_prefix, 0, "valueFrom", "path"))
        in diagnoses
    )
    assert IsPartialModel(code="M101", loc=(*loc_prefix, 0, "valueFrom")) in diagnoses
    assert IsPartialModel(code="DAG301", loc=(*loc_prefix, 1, "value")) in diagnoses
    assert IsPartialModel(code="M103", loc=(*loc_prefix, 2, "value")) in diagnoses
    assert IsPartialModel(code="M202", loc=(*loc_prefix, 3, "name")) in diagnoses
    assert IsPartialModel(code="M201", loc=(*loc_prefix, 4, "value")) in diagnoses
    assert IsPartialModel(code="M201", loc=(*loc_prefix, 4, "valueFrom")) in diagnoses


def test_check_argument_artifacts(diagnoses_logger):
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
                  - name: step1
                    template: compute
                    arguments:
                      artifacts:
                        - name: artifact1
                          from: workflow.invalid
                        - name: artifact1
                          raw:
                            data: "some data"
        """
    )
    diagnoses_logger(diagnoses)

    loc_prefix = ("spec", "templates", 0, "dag", "tasks", 0, "arguments", "artifacts")
    assert IsPartialModel(code="DAG103", loc=(*loc_prefix, 0, "name")) in diagnoses
    assert IsPartialModel(code="DAG103", loc=(*loc_prefix, 1, "name")) in diagnoses
    assert IsPartialModel(code="DAG302", loc=(*loc_prefix, 0, "from")) in diagnoses


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
            code="DAG201",
            loc=("spec", "templates", 0, "dag", "tasks", 0, "template"),
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            code="DAG202",
            loc=(
                "spec",
                "templates",
                1,
                "dag",
                "tasks",
                0,
                "templateRef",
                "template",
            ),
            msg=(
                AnyThing
                & HasSubstring(
                    "Template 'not-exist-template' does not exist in the workflow."
                )
                & HasSubstring("Available templates: 'another' or 'main'")
            ),
        )
        in diagnoses
    )
    assert (
        "Task 'external': Referenced template 'another-workflow' is not the same as current workflow 'demo'. Skipping."
        in caplog.text
    )
