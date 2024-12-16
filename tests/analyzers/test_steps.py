import json
import logging

from dirty_equals import IsPartialDict

import tugboat.analyze
from tests.utils import ContainsSubStrings

logger = logging.getLogger(__name__)


class TestRules:

    def test_check_argument_parameters(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_INPUT_PARAMETERS)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))

        loc_prefix = ("spec", "templates", 0, "steps", 0, 0, "arguments", "parameters")

        # M005: Found redundant field
        assert (
            IsPartialDict(
                {"code": "M005", "loc": (*loc_prefix, 0, "valueFrom", "path")}
            )
            in diagnoses
        )

        # TPL002: Duplicated input parameter name
        assert IsPartialDict({"code": "TPL002", "loc": (*loc_prefix, 0)}) in diagnoses
        assert IsPartialDict({"code": "TPL002", "loc": (*loc_prefix, 1)}) in diagnoses

        # VAR002: Invalid reference
        assert (
            IsPartialDict({"code": "VAR002", "loc": (*loc_prefix, 1, "value")})
            in diagnoses
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
                - name: message # TPL002
                  valueFrom:
                    path: /tmp/message  # M005
                - name: message # TPL002
                  value: "{{ workflow.invalid}}" # VAR002
"""
