import json
import logging

from dirty_equals import IsPartialDict

import tugboat.analyze

logger = logging.getLogger(__name__)


class TestRules:
    def test_analyze_template(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_AMBIGUOUS_TYPE)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert (
            IsPartialDict(
                {
                    "code": "M006",
                    "loc": ("spec", "templates", 0, "container"),
                }
            )
            in diagnoses
        )
        assert (
            IsPartialDict(
                {
                    "code": "M006",
                    "loc": ("spec", "templates", 0, "script"),
                }
            )
            in diagnoses
        )

    def test_check_input_parameters_1(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_DUPLICATE_ARGUMENTS)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert (
            IsPartialDict(
                {
                    "code": "TPL002",
                    "loc": ("spec", "templates", 0, "inputs", "parameters", 0),
                }
            )
            in diagnoses
        )
        assert (
            IsPartialDict(
                {
                    "code": "TPL002",
                    "loc": ("spec", "templates", 0, "inputs", "parameters", 1),
                }
            )
            in diagnoses
        )
        assert (
            IsPartialDict(
                {
                    "code": "M005",
                    "loc": (
                        "spec",
                        "templates",
                        0,
                        "inputs",
                        "parameters",
                        0,
                        "valueFrom",
                        "path",
                    ),
                }
            )
            in diagnoses
        )

    def test_check_input_parameters_2(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_REFERENCES)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert IsPartialDict(
            {
                "code": "VAR001",
                "loc": ("spec", "templates", 0, "inputs", "parameters", 0, "value"),
            }
        )
        assert IsPartialDict(
            {
                "code": "VAR002",
                "loc": ("spec", "templates", 0, "inputs", "parameters", 2, "value"),
                "msg": "Reference 'workflow.invalid' is not a valid parameter for the workflow 'test-'.",
                "input": "{{ workflow.invalid }}",
            }
        )

    def test_check_input_artifacts(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_DUPLICATE_ARGUMENTS)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert (
            IsPartialDict(
                {
                    "code": "TPL003",
                    "loc": ("spec", "templates", 0, "inputs", "artifacts", 0),
                }
            )
            in diagnoses
        )
        assert (
            IsPartialDict(
                {
                    "code": "TPL003",
                    "loc": ("spec", "templates", 0, "inputs", "artifacts", 1),
                }
            )
            in diagnoses
        )

    def test_check_output_parameters(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_DUPLICATE_ARGUMENTS)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert (
            IsPartialDict(
                {
                    "code": "TPL004",
                    "loc": ("spec", "templates", 0, "outputs", "parameters", 0),
                }
            )
            in diagnoses
        )
        assert (
            IsPartialDict(
                {
                    "code": "TPL004",
                    "loc": ("spec", "templates", 0, "outputs", "parameters", 1),
                }
            )
            in diagnoses
        )
        assert (
            IsPartialDict(
                {
                    "code": "M004",
                    "loc": (
                        "spec",
                        "templates",
                        0,
                        "outputs",
                        "parameters",
                        1,
                        "valueFrom",
                    ),
                }
            )
            in diagnoses
        )

    def test_check_output_artifacts(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_DUPLICATE_ARGUMENTS)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert (
            IsPartialDict(
                {
                    "code": "TPL005",
                    "loc": ("spec", "templates", 0, "outputs", "artifacts", 0),
                }
            )
            in diagnoses
        )
        assert (
            IsPartialDict(
                {
                    "code": "TPL005",
                    "loc": ("spec", "templates", 0, "outputs", "artifacts", 1),
                }
            )
            in diagnoses
        )
        assert (
            IsPartialDict(
                {
                    "code": "M004",
                    "loc": (
                        "spec",
                        "templates",
                        0,
                        "outputs",
                        "artifacts",
                        0,
                        "archive",
                    ),
                }
            )
            in diagnoses
        )


MANIFEST_AMBIGUOUS_TYPE = """
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  name: test
spec:
  templates:
    - name: main
      container:
        image: busybox:latest
      script:
        image: python:alpine3.13
        command: [ python ]
        source: print("hello world!")
"""

MANIFEST_DUPLICATE_ARGUMENTS = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  templates:
    - name: main
      inputs:
        parameters:
          - name: message # TPL002
            valueFrom:
              path: /malformed # M005
          - name: message # TPL002
        artifacts:
          - name: data # TPL003
          - name: data # TPL003
      container:
        image: busybox:latest
      outputs:
        parameters:
          - name: message # TPL004
            valueFrom:
              path: /data/message
          - name: message # TPL004, M004
        artifacts:
          - name: data # TPL005
            path: /data
            archive: {} # M004
          - name: data # TPL005
            path: /data
"""

MANIFEST_INVALID_REFERENCES = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  templates:
    - name: main
      inputs:
        parameters:
          - name: message-1
            value: "{{ workflow.name " # VAR001
          - name: message-2
            value: "{{ workflow.name }}"
          - name: message-3
            value: "{{ workflow.invalid }}" # VAR002
        artifacts:
          - name: data
"""
