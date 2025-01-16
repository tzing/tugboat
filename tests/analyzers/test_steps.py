import json
import logging

from dirty_equals import IsPartialDict

import tugboat.analyze

logger = logging.getLogger(__name__)


def test_check_argument_parameters():
    diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_INPUT_PARAMETERS)
    logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))

    loc_prefix = ("spec", "templates", 0, "steps", 0, 0, "arguments", "parameters")

    # M005: Found redundant field
    assert (
        IsPartialDict({"code": "M005", "loc": (*loc_prefix, 0, "valueFrom", "path")})
        in diagnoses
    )

    # STP002: Duplicated input parameter name
    assert (
        IsPartialDict({"code": "STP002", "loc": (*loc_prefix, 0, "name")}) in diagnoses
    )
    assert (
        IsPartialDict({"code": "STP002", "loc": (*loc_prefix, 1, "name")}) in diagnoses
    )

    # VAR002: Invalid reference
    assert (
        IsPartialDict({"code": "VAR002", "loc": (*loc_prefix, 1, "value")}) in diagnoses
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
                - name: message # STP002
                  valueFrom:
                    path: /tmp/message  # M005
                - name: message # STP002
                  value: "{{ workflow.invalid}}" # VAR002
"""


def test_check_argument_artifacts():
    diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_INPUT_ARTIFACTS)
    logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))

    loc_prefix = ("spec", "templates", 0, "steps", 0, 0, "arguments", "artifacts")

    # STP003: Duplicated input artifact name
    assert (
        IsPartialDict({"code": "STP003", "loc": (*loc_prefix, 0, "name")}) in diagnoses
    )
    assert (
        IsPartialDict({"code": "STP003", "loc": (*loc_prefix, 1, "name")}) in diagnoses
    )

    # VAR002: Invalid reference
    assert (
        IsPartialDict({"code": "VAR002", "loc": (*loc_prefix, 0, "from")}) in diagnoses
    )
    assert (
        IsPartialDict({"code": "VAR002", "loc": (*loc_prefix, 1, "raw", "data")})
        in diagnoses
    )
    assert (
        IsPartialDict({"code": "VAR002", "loc": (*loc_prefix, 2, "from")}) in diagnoses
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
                - name: message # STP003
                  from: "{{ workflow.invalid }}" # VAR002
                - name: message # STP003
                  raw:
                    data: "{{ workflow.invalid }}" # VAR002
                - name: another
                  from: workflow.invalid # VAR002
"""
