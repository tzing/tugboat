import json
import logging

import pytest
from dirty_equals import IsPartialDict

import tugboat.analyze
from tests.dirty_equals import ContainsSubStrings

logger = logging.getLogger(__name__)


def test_analyze_step():
    diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_STEP_USAGE)
    logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))

    loc = ("spec", "templates", 0, "steps", 0, 0)

    assert IsPartialDict({"code": "M006", "loc": (*loc, "template")}) in diagnoses
    assert IsPartialDict({"code": "M006", "loc": (*loc, "templateRef")}) in diagnoses

    assert (
        IsPartialDict(
            {"code": "STP004", "loc": ("spec", "templates", 0, "steps", 1, 0, "onExit")}
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


def test_check_argument_parameters():
    diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_INPUT_PARAMETERS)
    logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))

    loc_prefix = ("spec", "templates", 0, "steps", 0, 0, "arguments", "parameters")

    # M102: Found redundant field
    assert (
        IsPartialDict({"code": "M102", "loc": (*loc_prefix, 0, "valueFrom", "path")})
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
                    path: /tmp/message  # M102
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


def test_check_referenced_template(caplog: pytest.LogCaptureFixture):
    with caplog.at_level("DEBUG", "tugboat.analyzers.step"):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_TEMPLATE_REFERENCE)
    logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))

    assert (
        IsPartialDict(
            {
                "code": "STP005",
                "loc": ("spec", "templates", 0, "steps", 0, 0, "template"),
            }
        )
        in diagnoses
    )
    assert (
        IsPartialDict(
            {
                "code": "STP006",
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


def test_check_fields_references():
    diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_FIELDS_REFERENCES)
    logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))

    assert IsPartialDict(
        {
            "code": "VAR002",
            "loc": ("spec", "templates", 0, "steps", 0, 0, "when"),
        }
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
