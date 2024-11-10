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
