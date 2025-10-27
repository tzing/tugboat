import pytest

from tests.dirty_equals import ContainsSubStrings, IsPartialModel
from tugboat.engine import analyze_yaml_stream


def test_analyze_task(diagnoses_logger):
    diagnoses = analyze_yaml_stream(
        """
        apiVersion: argoproj.io/v1alpha1
        kind: Workflow
        metadata:
          generateName: test-
        spec:
          entrypoint: main
          templates:
            - name: main
              dag:
                tasks:
                  - name: task-2
                    depends: task-1
                    dependencies:
                      - task-1
                    template: test
                  - name: deprecated
                    onExit: exit
                    template: print-message
        """
    )
    diagnoses_logger(diagnoses)

    loc = ("spec", "templates", 0, "dag", "tasks", 0)
    assert IsPartialModel({"code": "M201", "loc": (*loc, "depends")}) in diagnoses
    assert IsPartialModel({"code": "M201", "loc": (*loc, "dependencies")}) in diagnoses
