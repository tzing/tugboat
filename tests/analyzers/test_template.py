import json
import logging

from dirty_equals import IsPartialDict

import tugboat.analyze
from tests.utils import ContainsSubStrings

logger = logging.getLogger(__name__)


class TestInputRules:

    def test_check_input_parameters(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_INPUT_PARAMETERS)
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
        assert (
            IsPartialDict(
                {
                    "code": "VAR001",
                    "loc": ("spec", "templates", 0, "inputs", "parameters", 1, "value"),
                }
            )
            in diagnoses
        )
        assert (
            IsPartialDict(
                {
                    "code": "VAR002",
                    "loc": ("spec", "templates", 0, "inputs", "parameters", 2, "value"),
                    "msg": "The parameter reference 'workflow.invalid' used in parameter 'message-3' is invalid.",
                    "input": "{{ workflow.invalid}}",
                }
            )
            in diagnoses
        )

    def test_check_input_artifacts(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_INPUT_ARTIFACTS)
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
        assert (
            IsPartialDict(
                {
                    "code": "VAR002",
                    "loc": (
                        "spec",
                        "templates",
                        0,
                        "inputs",
                        "artifacts",
                        0,
                        "raw",
                        "data",
                    ),
                    "msg": ContainsSubStrings(
                        "The parameter reference 'workflow.namee' used in artifact 'data' is invalid.",
                    ),
                    "fix": "{{ workflow.name }}",
                }
            )
            in diagnoses
        )
        assert (
            IsPartialDict(
                {
                    "code": "VAR002",
                    "loc": (
                        "spec",
                        "templates",
                        0,
                        "inputs",
                        "artifacts",
                        1,
                        "from",
                    ),
                    "msg": "The artifact reference 'invalid' used in artifact 'data' is invalid.",
                }
            )
            in diagnoses
        )


MANIFEST_INVALID_INPUT_PARAMETERS = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  entrypoint: test
  templates:
    - name: main
      inputs:
        parameters:
          - name: message # TPL002
            valueFrom:
              path: /malformed # M005
          - name: message # TPL002
            value: "{{ workflow.name " # VAR001
          - name: message-3
            value: "{{ workflow.invalid}}" # VAR002
"""

MANIFEST_INVALID_INPUT_ARTIFACTS = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  entrypoint: test
  templates:
    - name: test
      inputs:
        artifacts:
          - name: data # TPL003
            raw:
              data:
                This is a message from {{ workflow.namee }}. # VAR002
          - name: data # TPL003
            from: "{{ invalid }}" # VAR002
"""


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

    def test_check_output_parameters(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_OUTPUT_PARAMETERS)
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
                    "code": "VAR002",
                    "loc": (
                        "spec",
                        "templates",
                        0,
                        "outputs",
                        "parameters",
                        1,
                        "valueFrom",
                        "parameter",
                    ),
                }
            )
            in diagnoses
        )

    def test_check_output_artifacts(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_OUTPUT_ARTIFACTS)
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
        assert (
            IsPartialDict(
                {
                    "code": "VAR002",
                    "loc": ("spec", "templates", 0, "outputs", "artifacts", 1, "from"),
                }
            )
            in diagnoses
        )

    def test_check_field_references(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_REFERENCES)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert (
            IsPartialDict(
                {
                    "code": "VAR002",
                    "loc": ("spec", "templates", 0, "container", "args", 1),
                    "msg": "The parameter reference 'inputs.parameters.command' used in template 'container-template' is invalid.",
                    "fix": "{{ inputs.parameters.cmd }}",
                }
            )
            in diagnoses
        )
        assert (
            IsPartialDict(
                {
                    "code": "VAR002",
                    "loc": ("spec", "templates", 1, "script", "source"),
                    "msg": "The parameter reference 'inputs.artifacts.data' used in template 'script-template' is invalid.",
                    "fix": "{{ inputs.artifacts.data.path }}",
                }
            )
            in diagnoses
        )

    def test_check_duplicate_step_names(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_DUPLICATE_STEP_NAMES)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert (
            IsPartialDict(
                {
                    "code": "STP001",
                    "loc": ("spec", "templates", 0, "steps", 0, 0, "name"),
                }
            )
            in diagnoses
        )
        assert (
            IsPartialDict(
                {
                    "code": "STP001",
                    "loc": ("spec", "templates", 0, "steps", 1, 0, "name"),
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


MANIFEST_INVALID_OUTPUT_PARAMETERS = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  entrypoint: main
  templates:
    - name: main
      container:
        image: busybox:latest
      outputs:
        parameters:
          - name: message # TPL004
          - name: message # TPL004
            valueFrom:
              parameter: "{{ workflow.invalid}}" # VAR002
"""

MANIFEST_INVALID_OUTPUT_ARTIFACTS = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  templates:
    - name: main
      outputs:
        artifacts:
          - name: data # TPL005
            path: /data
            archive: {} # M004
          - name: data # TPL005
            from: '{{ invalid }}'
"""

MANIFEST_INVALID_REFERENCES = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  entrypoint: container-template
  templates:
    - name: container-template
      inputs:
        parameters:
          - name: cmd
      container:
        image: python:alpine3.13
        command: [ python ]
        args:
          - -c
          - '{{ inputs.parameters.command }}'  # VAR002
    - name: script-template
      inputs:
        artifacts:
          - name: data
      script:
        image: python:alpine3.13
        command: [ python ]
        source: |-
          print('Hello world, {{ inputs.artifacts.data }}!')  # VAR002
"""

MANIFEST_DUPLICATE_STEP_NAMES = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: steps-
spec:
  entrypoint: hello-hello
  templates:
    - name: hello-hello
      steps:
        - - name: hello
            #     ^^^^^ This step is duplicated
            template: print-message
            arguments:
              parameters:
                - name: message
                  value: "hello-1"
        - - name: hello
            #     ^^^^^ This step is duplicated
            template: print-message
            arguments:
              parameters:
                - name: message
                  value: "hello-2"
"""
