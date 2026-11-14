import json

import pytest
from dirty_equals import AnyThing

from tests.dirty_equals import HasSubstring, IsPartialModel
from tugboat.engine import analyze_yaml_stream


def analyze_dependencies(tasks):
    return analyze_yaml_stream(
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
                tasks: TASKS
            - name: run
              container:
                image: alpine
        """.replace(
            "TASKS", json.dumps([{"template": "run", **task} for task in tasks])
        )
    )


@pytest.mark.parametrize(
    ("tasks", "cycle_names"),
    [
        ([{"name": "a", "dependencies": ["a"]}], {"a"}),
        (
            [
                {"name": "a", "dependencies": ["c", "missing"]},
                {"name": "b", "dependencies": ["a"]},
                {"name": "c", "dependencies": ["b"]},
                {"name": "downstream", "dependencies": ["a"]},
            ],
            {"a", "b", "c"},
        ),
        (
            [
                {"name": "root"},
                {"name": "a", "dependencies": ["b"]},
                {"name": "b", "dependencies": ["a"]},
            ],
            {"a", "b"},
        ),
    ],
)
def test_circular_dependencies(tasks, cycle_names):
    diagnoses = analyze_dependencies(tasks)
    cycles = [diag for diag in diagnoses if diag.code == "DAG501"]
    assert len(cycles) == 1
    assert cycles[0].loc == ("spec", "templates", 0, "dag", "tasks")
    for name in cycle_names:
        assert f"'{name}'" in cycles[0].msg
    assert "'downstream'" not in cycles[0].msg


@pytest.mark.parametrize(
    "tasks",
    [
        [],
        [{"name": "a"}],
        [
            {"name": "end", "dependencies": ["left", "right"]},
            {"name": "left", "dependencies": ["root"]},
            {"name": "right", "dependencies": ["root", "root"]},
            {"name": "root", "dependencies": []},
        ],
        [{"name": "a", "dependencies": ["missing"]}],
        [
            {"name": "a", "dependencies": ["a"]},
            {"name": "a"},
        ],
        [
            {"name": "a", "depends": "b || missing.Succeeded"},
            {"name": "b", "dependencies": ["a"]},
        ],
    ],
)
def test_dependencies_without_detectable_cycle(tasks):
    diagnoses = analyze_dependencies(tasks)
    assert not any(diag.code == "DAG501" for diag in diagnoses)


def test_unknown_dependencies():
    diagnoses = analyze_dependencies(
        [
            {"name": "build"},
            {"name": "publish", "dependencies": ["build", "biuld"]},
        ]
    )
    unknown = [diag for diag in diagnoses if diag.code == "DAG502"]
    assert len(unknown) == 1
    assert (
        IsPartialModel(
            loc=("spec", "templates", 0, "dag", "tasks", 1, "dependencies", 1),
            input="biuld",
            fix="build",
        )
        == unknown[0]
    )


def test_unknown_dependency_without_suggestion():
    diagnoses = analyze_dependencies([{"name": "a", "dependencies": ["missing"]}])
    assert IsPartialModel(code="DAG502", input="missing", fix=None) in diagnoses


def test_depends_is_not_checked():
    diagnoses = analyze_dependencies([{"name": "a", "depends": "missing"}])
    assert not any(diag.code in {"DAG501", "DAG502"} for diag in diagnoses)


def test_dependency_must_exist_in_same_dag():
    diagnoses = analyze_dependencies([{"name": "a", "dependencies": ["run"]}])
    assert IsPartialModel(code="DAG502", input="run") in diagnoses


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
    assert IsPartialModel(code="M202", loc=(*loc_prefix, 2, "name")) in diagnoses
    assert IsPartialModel(code="M201", loc=(*loc_prefix, 3, "value")) in diagnoses
    assert IsPartialModel(code="M201", loc=(*loc_prefix, 3, "valueFrom")) in diagnoses


def test_check_argument_parameters_usage(diagnoses_logger):
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
                  - name: hello
                    template: print-message
                    arguments:
                      parameters:
                        - name: role
                          value: admin
                        - name: extra-param
                          value: blah
            - name: print-message
              inputs:
                parameters:
                  - name: message
                  - name: role
                    default: user
        """
    )
    diagnoses_logger(diagnoses)

    loc_prefix = ("spec", "templates", 0, "dag", "tasks", 0, "arguments", "parameters")
    assert IsPartialModel(code="DAG304", loc=(*loc_prefix, 1, "name")) in diagnoses
    assert IsPartialModel(code="DAG305", loc=loc_prefix) in diagnoses


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
                          from: "{{ workflow.invalid }}"
                        - name: artifact1
                          raw:
                            data: "{{ workflow.invalid }}"
        """
    )
    diagnoses_logger(diagnoses)

    loc_prefix = ("spec", "templates", 0, "dag", "tasks", 0, "arguments", "artifacts")
    assert IsPartialModel(code="DAG103", loc=(*loc_prefix, 0, "name")) in diagnoses
    assert IsPartialModel(code="DAG103", loc=(*loc_prefix, 1, "name")) in diagnoses
    assert IsPartialModel(code="DAG302", loc=(*loc_prefix, 0, "from")) in diagnoses
    assert (
        IsPartialModel(code="DAG303", loc=(*loc_prefix, 1, "raw", "data")) in diagnoses
    )


def test_check_argument_artifact_usage(diagnoses_logger):
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
                  - name: hello
                    template: print-message
                    arguments:
                      artifacts:
                        - name: role
                          from: "{{ workflow.artifact-role }}"
                        - name: extra-artifact
                          from: "{{ workflow.artifact-extra }}"

            - name: print-message
              inputs:
                artifacts:
                  - name: message
                  - name: role
                    optional: true
        """
    )
    diagnoses_logger(diagnoses)

    loc_prefix = ("spec", "templates", 0, "dag", "tasks", 0, "arguments", "artifacts")

    assert IsPartialModel(code="DAG306", loc=(*loc_prefix, 1, "name")) in diagnoses
    assert IsPartialModel(code="DAG307", loc=loc_prefix) in diagnoses


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


def test_check_inline_template(diagnoses_logger):
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
                    inline:
                      dag:
                        tasks: []
        """
    )
    diagnoses_logger(diagnoses)

    assert (
        IsPartialModel(
            code="DAG401",
            loc=(
                "spec",
                "templates",
                0,
                "dag",
                "tasks",
                0,
                "inline",
                "dag",
            ),
        )
        in diagnoses
    )
