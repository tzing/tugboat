import json
import logging

from dirty_equals import IsPartialDict

import tugboat.analyze

logger = logging.getLogger(__name__)


class TestRules:
    def test_check_metadata_1(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_NAME_TOO_LONG)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert IsPartialDict({"code": "M302"}) in diagnoses

    def test_check_metadata_2(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_USE_GENERATE_NAME)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert IsPartialDict({"code": "WT001"}) in diagnoses

    def test_check_spec(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_USE_GENERATE_NAME)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert IsPartialDict({"code": "M201"}) in diagnoses

    def test_check_entrypoint(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_ENTRYPOINT)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert IsPartialDict({"code": "WT201"}) in diagnoses
        assert IsPartialDict({"code": "TPL101"}) in diagnoses


MANIFEST_NAME_TOO_LONG = """
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  name: a-very-long-name-that-is-definitely-too-long-for-argo-workflow-templates  # WT201
spec:
  templates: []
"""


MANIFEST_USE_GENERATE_NAME = """
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  generateName: test-workflow-  # WT201
spec:
  templates: []
  workflowTemplateRef:  # M201
    name: test
"""

MANIFEST_INVALID_ENTRYPOINT = """
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  name: test
spec:
  entrypoint: main  # WT201
  templates:
    - name: hello  # TPL101
      container:
        image: busybox
    - name: world
      container:
        image: busybox
    - name: hello  # TPL101
      container:
        image: busybox
"""


def test_check_argument_parameters():
    diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_MALFORMED_PARAMETERS)
    logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))

    # WT101: Duplicated parameter name
    assert (
        IsPartialDict(
            {"code": "WT101", "loc": ("spec", "arguments", "parameters", 0, "name")}
        )
        in diagnoses
    )
    assert (
        IsPartialDict(
            {"code": "WT101", "loc": ("spec", "arguments", "parameters", 1, "name")}
        )
        in diagnoses
    )

    # M103: Type error
    assert (
        IsPartialDict(
            {"code": "M103", "loc": ("spec", "arguments", "parameters", 2, "value")}
        )
        in diagnoses
    )


MANIFEST_MALFORMED_PARAMETERS = """
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  name: test
spec:
  arguments:
    parameters:
      - name: message  # WT101
        valueFrom:
          configMapKeyRef:
            name: my-config
            key: my-key
      - name: message  # WT101
        default: foo
      - name: param-3
        value:
          foo: bar # M103
"""


def test_check_argument_artifacts():
    diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_MALFORMED_ARTIFACTS)
    logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))

    # WT102: Duplicated input artifact name
    assert (
        IsPartialDict(
            {"code": "WT102", "loc": ("spec", "arguments", "artifacts", 0, "name")}
        )
        in diagnoses
    )
    assert (
        IsPartialDict(
            {"code": "WT102", "loc": ("spec", "arguments", "artifacts", 1, "name")}
        )
        in diagnoses
    )

    # M201: Invalid reference
    assert (
        IsPartialDict(
            {
                "code": "M201",
                "loc": ("spec", "arguments", "artifacts", 0, "raw"),
            }
        )
        in diagnoses
    )
    assert (
        IsPartialDict(
            {
                "code": "M201",
                "loc": ("spec", "arguments", "artifacts", 0, "s3"),
            }
        )
        in diagnoses
    )

    # M102: Found redundant field
    assert (
        IsPartialDict(
            {
                "code": "M102",
                "loc": ("spec", "arguments", "artifacts", 2, "value"),
            }
        )
        in diagnoses
    )


MANIFEST_MALFORMED_ARTIFACTS = """
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  name: test
spec:
  arguments:
    artifacts:
      - name: data  # WT102
        raw:  # M201
          data: world
        s3:  # M201
          key: my-file
      - name: data  # WT102
        raw:
          data: hello
      - name: artifact-3
        value: foo  # M102
"""
