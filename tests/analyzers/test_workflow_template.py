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
        assert IsPartialDict({"code": "WT004"}) in diagnoses

    def test_check_spec(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_USE_GENERATE_NAME)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert IsPartialDict({"code": "M201"}) in diagnoses

    def test_check_entrypoint(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_ENTRYPOINT)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert IsPartialDict({"code": "WT001"}) in diagnoses
        assert IsPartialDict({"code": "TPL101"}) in diagnoses

    def test_check_arguments(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_MALFORMED_ARGUMENTS)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))

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


MANIFEST_NAME_TOO_LONG = """
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  name: a-very-long-name-that-is-definitely-too-long-for-argo-workflow-templates  # WT001
spec:
  templates: []
"""


MANIFEST_USE_GENERATE_NAME = """
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  generateName: test-workflow-  # WT001
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
  entrypoint: main  # WT001
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

MANIFEST_MALFORMED_ARGUMENTS = """
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
    artifacts:
      - name: data  # WT102
        raw:  # M201
          data: world
        s3:  # M201
          key: my-file
      - name: data  # WT102
        raw:
          data: hello
"""
