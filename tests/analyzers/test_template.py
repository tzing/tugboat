import json
import logging

from dirty_equals import IsPartialDict

import tugboat.analyze

logger = logging.getLogger(__name__)


class TestRules:
    def test_analyze_template(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_AMBIGUOUS_TYPE)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert (
            IsPartialDict(
                {
                    "code": "M006",
                    "loc": ("spec", "templates", 0, "container"),
                }
            )
            in diagnostics
        )
        assert (
            IsPartialDict(
                {
                    "code": "M006",
                    "loc": ("spec", "templates", 0, "script"),
                }
            )
            in diagnostics
        )

    def test_check_input_parameters(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_DUPLICATE_ARGUMENTS)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert (
            IsPartialDict(
                {
                    "code": "TPL002",
                    "loc": ("spec", "templates", 0, "inputs", "parameters", 0),
                }
            )
            in diagnostics
        )
        assert (
            IsPartialDict(
                {
                    "code": "TPL002",
                    "loc": ("spec", "templates", 0, "inputs", "parameters", 1),
                }
            )
            in diagnostics
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
            in diagnostics
        )

    def test_check_input_artifacts(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_DUPLICATE_ARGUMENTS)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert (
            IsPartialDict(
                {
                    "code": "TPL003",
                    "loc": ("spec", "templates", 0, "inputs", "artifacts", 0),
                }
            )
            in diagnostics
        )
        assert (
            IsPartialDict(
                {
                    "code": "TPL003",
                    "loc": ("spec", "templates", 0, "inputs", "artifacts", 1),
                }
            )
            in diagnostics
        )

    def test_check_output_parameters(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_DUPLICATE_ARGUMENTS)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert (
            IsPartialDict(
                {
                    "code": "TPL004",
                    "loc": ("spec", "templates", 0, "outputs", "parameters", 0),
                }
            )
            in diagnostics
        )
        assert (
            IsPartialDict(
                {
                    "code": "TPL004",
                    "loc": ("spec", "templates", 0, "outputs", "parameters", 1),
                }
            )
            in diagnostics
        )
        assert (
            IsPartialDict(
                {
                    "code": "M004",
                    "loc": ("spec", "templates", 0, "outputs", "parameters", 1),
                }
            )
            in diagnostics
        )

    def test_check_output_artifacts(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_DUPLICATE_ARGUMENTS)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert (
            IsPartialDict(
                {
                    "code": "TPL005",
                    "loc": ("spec", "templates", 0, "outputs", "artifacts", 0),
                }
            )
            in diagnostics
        )
        assert (
            IsPartialDict(
                {
                    "code": "TPL005",
                    "loc": ("spec", "templates", 0, "outputs", "artifacts", 1),
                }
            )
            in diagnostics
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
            in diagnostics
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
