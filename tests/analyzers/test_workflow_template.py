import json
import logging

import ruamel.yaml
from dirty_equals import IsPartialDict

import tugboat.analyze

logger = logging.getLogger(__name__)
yaml = ruamel.yaml.YAML(typ="safe")


class TestRules:
    def test_check_metadata_1(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_NAME_TOO_LONG)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert IsPartialDict({"code": "M009"}) in diagnostics

    def test_check_metadata_2(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_USE_GENERATE_NAME)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert IsPartialDict({"code": "WT005"}) in diagnostics

    def test_check_spec(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_USE_GENERATE_NAME)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert IsPartialDict({"code": "M006"}) in diagnostics

    def test_check_entrypoint(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_ENTRYPOINT)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert IsPartialDict({"code": "WT001"}) in diagnostics
        assert IsPartialDict({"code": "WT002"}) in diagnostics

    def test_check_arguments(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_MALFORMED_ARGUMENTS)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))

        assert (
            IsPartialDict(
                {"code": "WT003", "loc": ("spec", "arguments", "parameters", 0)}
            )
            in diagnostics
        )
        assert (
            IsPartialDict(
                {"code": "WT003", "loc": ("spec", "arguments", "parameters", 1)}
            )
            in diagnostics
        )

        assert (
            IsPartialDict(
                {"code": "WT004", "loc": ("spec", "arguments", "artifacts", 0)}
            )
            in diagnostics
        )
        assert (
            IsPartialDict(
                {"code": "WT004", "loc": ("spec", "arguments", "artifacts", 1)}
            )
            in diagnostics
        )

        assert (
            IsPartialDict(
                {
                    "code": "M006",
                    "loc": ("spec", "arguments", "artifacts", 0, "raw"),
                }
            )
            in diagnostics
        )
        assert (
            IsPartialDict(
                {
                    "code": "M006",
                    "loc": ("spec", "arguments", "artifacts", 0, "s3"),
                }
            )
            in diagnostics
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
  workflowTemplateRef:  # M006
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
    - name: hello  # WT002
      container:
        image: busybox
    - name: world
      container:
        image: busybox
    - name: hello  # WT002
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
      - name: message  # WT003
        valueFrom:
          configMapKeyRef:
            name: my-config
            key: my-key
      - name: message  # WT003
        default: foo
    artifacts:
      - name: data  # WT004
        raw:  # M006
          data: world
        s3:  # M006
          key: my-file
      - name: data  # WT004
        raw:
          data: hello
"""
