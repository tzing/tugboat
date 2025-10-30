import pytest

from tests.dirty_equals import ContainsSubStrings, IsPartialModel
from tugboat.engine import analyze_yaml_stream


def test_analyze_step(diagnoses_logger):
    diagnoses = analyze_yaml_stream(MANIFEST_INVALID_STEP_USAGE)
    diagnoses_logger(diagnoses)

    loc = ("spec", "templates", 0, "steps", 0, 0)

    assert IsPartialModel({"code": "M201", "loc": (*loc, "template")}) in diagnoses
    assert IsPartialModel({"code": "M201", "loc": (*loc, "templateRef")}) in diagnoses

    assert (
        IsPartialModel(
            {"code": "STP901", "loc": ("spec", "templates", 0, "steps", 1, 0, "onExit")}
        )
        in diagnoses
    )


MANIFEST_INVALID_STEP_USAGE = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  entrypoint: main
  templates:
    - name: main
      steps:
        - - name: step1
            template: test
            templateRef:
              name: test
              template: test
        - - name: deprecated
            onExit: exit
            template: print-message
            arguments:
              parameters: [{name: message, value: "hello1"}]
"""


def test_check_argument_parameters(diagnoses_logger):
    diagnoses = analyze_yaml_stream(MANIFEST_INVALID_INPUT_PARAMETERS)
    diagnoses_logger(diagnoses)

    loc_prefix = ("spec", "templates", 0, "steps", 0, 0, "arguments", "parameters")

    # M102: Found redundant field
    assert (
        IsPartialModel({"code": "M102", "loc": (*loc_prefix, 0, "valueFrom", "path")})
        in diagnoses
    )

    # M103: Type error
    assert (
        IsPartialModel({"code": "M103", "loc": (*loc_prefix, 2, "value")}) in diagnoses
    )

    # STP102: Duplicated input parameter name
    assert (
        IsPartialModel({"code": "STP102", "loc": (*loc_prefix, 0, "name")}) in diagnoses
    )
    assert (
        IsPartialModel({"code": "STP102", "loc": (*loc_prefix, 1, "name")}) in diagnoses
    )

    # STP301: Invalid reference
    assert (
        IsPartialModel({"code": "STP301", "loc": (*loc_prefix, 1, "value")})
        in diagnoses
    )


MANIFEST_INVALID_INPUT_PARAMETERS = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  entrypoint: main
  templates:
    - name: main
      steps:
        - - name: step1
            template: test
            arguments:
              parameters:
                - name: message # STP102
                  valueFrom:
                    path: /tmp/message  # M102
                - name: message # STP102
                  value: "{{ workflow.invalid}}" # STP301
                - name: param-3
                  value:
                    foo: bar # M103
"""


def test_check_argument_parameters_usage(diagnoses_logger):
    diagnoses = analyze_yaml_stream(MANIFEST_INVALID_PARAMETER_USAGE)
    diagnoses_logger(diagnoses)

    loc_steps = ("spec", "templates", 0, "steps")

    # STP304: unexpected parameter
    assert (
        IsPartialModel(
            code="STP304",
            loc=(*loc_steps, 0, 1, "arguments", "parameters", 1, "name"),
        )
        in diagnoses
    )

    # STP305: missing parameter
    assert (
        IsPartialModel(
            code="STP305",
            loc=(*loc_steps, 0, 0, "arguments", "parameters"),
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            code="STP305",
            loc=(*loc_steps, 0, 1, "arguments", "parameters"),
        )
        in diagnoses
    )


MANIFEST_INVALID_PARAMETER_USAGE = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  entrypoint: main
  templates:
    - name: main
      steps:
        - - name: hello
            template: print-message
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


def test_check_argument_artifacts(diagnoses_logger):
    diagnoses = analyze_yaml_stream(MANIFEST_INVALID_INPUT_ARTIFACTS)
    diagnoses_logger(diagnoses)

    loc_prefix = ("spec", "templates", 0, "steps", 0, 0, "arguments", "artifacts")

    # STP103: Duplicated input artifact name
    assert (
        IsPartialModel({"code": "STP103", "loc": (*loc_prefix, 0, "name")}) in diagnoses
    )
    assert (
        IsPartialModel({"code": "STP103", "loc": (*loc_prefix, 1, "name")}) in diagnoses
    )

    # STP302: Invalid reference
    assert (
        IsPartialModel({"code": "STP302", "loc": (*loc_prefix, 0, "from")}) in diagnoses
    )
    assert (
        IsPartialModel({"code": "STP303", "loc": (*loc_prefix, 1, "raw", "data")})
        in diagnoses
    )
    assert (
        IsPartialModel({"code": "STP302", "loc": (*loc_prefix, 2, "from")}) in diagnoses
    )

    # M102: Found redundant field
    assert (
        IsPartialModel({"code": "M102", "loc": (*loc_prefix, 3, "value")}) in diagnoses
    )


MANIFEST_INVALID_INPUT_ARTIFACTS = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  name: test-
spec:
  entrypoint: main
  templates:
    - name: main
      steps:
        - - name: hello
            template: print-message
            arguments:
              artifacts:
                - name: message # STP103
                  from: "{{ workflow.invalid }}" # STP302
                - name: message # STP103
                  raw:
                    data: "{{ workflow.invalid }}" # STP303
                - name: artifact-2
                  from: workflow.invalid # STP302
                - name: artifact-3
                  value: foo # M102
"""


def test_check_argument_artifact_usage(diagnoses_logger):
    diagnoses = analyze_yaml_stream(MANIFEST_INVALID_ARTIFACT_USAGE)
    diagnoses_logger(diagnoses)

    loc_steps = ("spec", "templates", 0, "steps")

    # STP306: unexpected artifact
    assert (
        IsPartialModel(
            code="STP306",
            loc=(*loc_steps, 0, 1, "arguments", "artifacts", 1, "name"),
        )
        in diagnoses
    )

    # STP307: missing artifact
    assert (
        IsPartialModel(
            code="STP307",
            loc=(*loc_steps, 0, 0, "arguments", "artifacts"),
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            code="STP307",
            loc=(*loc_steps, 0, 1, "arguments", "artifacts"),
        )
        in diagnoses
    )


MANIFEST_INVALID_ARTIFACT_USAGE = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  entrypoint: main
  templates:
    - name: main
      steps:
        - - name: hello
            template: print-message
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


def test_check_referenced_template(caplog: pytest.LogCaptureFixture, diagnoses_logger):
    with caplog.at_level("DEBUG", "tugboat.analyzers.step"):
        diagnoses = analyze_yaml_stream(MANIFEST_INVALID_TEMPLATE_REFERENCE)
    diagnoses_logger(diagnoses)

    assert (
        IsPartialModel(
            {
                "code": "STP201",
                "loc": ("spec", "templates", 0, "steps", 0, 0, "template"),
            }
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            {
                "code": "STP202",
                "loc": (
                    "spec",
                    "templates",
                    1,
                    "steps",
                    0,
                    0,
                    "templateRef",
                    "template",
                ),
                "msg": ContainsSubStrings(
                    "Template 'not-exist-template' does not exist in the workflow.",
                    "Available templates: 'another' or 'self-reference'",
                ),
            }
        )
        in diagnoses
    )

    assert (
        "Step 'goodbye': "
        "Referenced template 'another-workflow' is not the same as current workflow 'demo'."
        in caplog.text
    )


MANIFEST_INVALID_TEMPLATE_REFERENCE = """
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  name: demo
spec:
  templates:
    - name: self-reference
      steps:
        - - name: hello
            template: self-reference

    - name: invalid-reference
      steps:
        - - name: hello
            templateRef:
              name: demo
              template: not-exist-template
          - name: goodbye
            templateRef:
              name: another-workflow
              template: whatever

    - name: another
      suspend: {}
"""


def test_check_fields_references(diagnoses_logger):
    diagnoses = analyze_yaml_stream(MANIFEST_FIELDS_REFERENCES)
    diagnoses_logger(diagnoses)

    assert (
        IsPartialModel(
            {
                "code": "VAR002",
                "loc": ("spec", "templates", 0, "steps", 0, 0, "when"),
            }
        )
        in diagnoses
    )


MANIFEST_FIELDS_REFERENCES = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: exit-handler-step-level-
spec:
  entrypoint: main
  templates:
    - name: main
      steps:
        - - name: hello
            when: "{{ count }} > 0"
            template: print-message
"""


def test_check_inline_template(diagnoses_logger):
    diagnoses = analyze_yaml_stream(MANIFEST_INLINE_TEMPLATE)
    diagnoses_logger(diagnoses)

    assert (
        IsPartialModel(
            {
                "code": "STP401",
                "loc": ("spec", "templates", 0, "steps", 0, 0, "inline", "steps"),
            }
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            {
                "code": "M101",
                "loc": ("spec", "templates", 0, "steps", 0, 1, "inline"),
            }
        )
        in diagnoses
    )


MANIFEST_INLINE_TEMPLATE = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  entrypoint: main
  templates:
    - name: main
      steps:
        - - name: foo
            inline:
              steps:
                - - name: nested-step
                    template: not-exist-template
          - name: bar
            inline:
              inputs:
                parameters:
                  - name: message
"""
