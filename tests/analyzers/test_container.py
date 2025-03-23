import json
import logging

from dirty_equals import IsPartialDict

import tugboat.analyze

logger = logging.getLogger(__name__)


def test_analyze_template():
    diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_REFERENCE)
    logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))

    assert (
        IsPartialDict(
            {
                "code": "VAR002",
                "loc": ("spec", "templates", 0, "script", "source"),
                "input": "{{ inputs.parameters.foo }}",
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
"""


def test_check_input_artifacts():
    diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_MISSING_INPUT_PATH)
    logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))

    assert (
        IsPartialDict(
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


def test_check_output():
    diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_MISSING_OUTPUT_PATH)
    logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))

    assert (
        IsPartialDict(
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
        IsPartialDict(
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
        IsPartialDict(
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
