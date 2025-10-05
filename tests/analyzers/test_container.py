from tests.dirty_equals import IsPartialModel
from tugboat.engine import analyze_yaml_stream


def test_analyze_template(diagnoses_logger):
    diagnoses = analyze_yaml_stream(MANIFEST_INVALID_REFERENCE)
    diagnoses_logger(diagnoses)

    assert (
        IsPartialModel(
            {
                "code": "VAR002",
                "loc": ("spec", "templates", 0, "script", "source"),
                "input": "{{ inputs.parameters.foo }}",
            }
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            {
                "code": "TPL304",
                "loc": (
                    "spec",
                    "templates",
                    0,
                    "script",
                    "resources",
                    "requests",
                    "cpu",
                ),
                "input": "1.5",
            }
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            {
                "code": "TPL304",
                "loc": (
                    "spec",
                    "templates",
                    0,
                    "script",
                    "resources",
                    "requests",
                    "memory",
                ),
                "input": "100Gi",
            }
        )
        in diagnoses
    )


MANIFEST_INVALID_REFERENCE = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  name: test
spec:
  entrypoint: main
  templates:
    - name: main
      script:
        image: busybox
        source: |
          echo "{{ inputs.parameters.foo }}"
        resources:
          requests:
            memory: 100Gi
            cpu: "1.5"
          limits:
            memory: 10Gi
            cpu: 1000m
"""


def test_check_input_artifacts(diagnoses_logger):
    diagnoses = analyze_yaml_stream(MANIFEST_MISSING_INPUT_PATH)
    diagnoses_logger(diagnoses)

    assert (
        IsPartialModel(
            {
                "code": "M101",
                "loc": ("spec", "templates", 0, "inputs", "artifacts", 0, "path"),
            }
        )
        in diagnoses
    )


MANIFEST_MISSING_INPUT_PATH = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  name: test
spec:
  entrypoint: main
  templates:
    - name: main
      inputs:
        artifacts:
          - name: data
      container:
        image: busybox
"""


def test_check_output(diagnoses_logger):
    diagnoses = analyze_yaml_stream(MANIFEST_MISSING_OUTPUT_PATH)
    diagnoses_logger(diagnoses)

    assert (
        IsPartialModel(
            {
                "code": "M101",
                "loc": (
                    "spec",
                    "templates",
                    0,
                    "outputs",
                    "parameters",
                    0,
                    "valueFrom",
                ),
            }
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            {
                "code": "M101",
                "loc": (
                    "spec",
                    "templates",
                    0,
                    "outputs",
                    "parameters",
                    1,
                    "valueFrom",
                    "path",
                ),
            }
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            {
                "code": "M101",
                "loc": ("spec", "templates", 0, "outputs", "artifacts", 0, "path"),
            }
        )
        in diagnoses
    )


MANIFEST_MISSING_OUTPUT_PATH = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  name: test
spec:
  entrypoint: main
  templates:
    - name: main
      outputs:
        parameters:
          - name: foo
          - name: bar
            valueFrom:
              default: bar
        artifacts:
          - name: baz
      container:
        image: busybox
"""
