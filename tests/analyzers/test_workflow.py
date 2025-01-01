import itertools
import json
import logging

from dirty_equals import IsPartialDict

import tugboat.analyze
from tugboat.core import hookimpl
from tugboat.schemas import Workflow, WorkflowTemplate

logger = logging.getLogger(__name__)


class TestParseManifest:
    def test_workflow(self, stable_hooks):
        manifest = stable_hooks.parse_manifest(
            manifest={
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "Workflow",
                "metadata": {"generateName": "hello-world-"},
                "spec": {
                    "entrypoint": "hello-world",
                    "templates": [
                        {
                            "name": "hello-world",
                            "container": {
                                "image": "busybox",
                                "command": ["echo"],
                                "args": ["hello world"],
                            },
                        }
                    ],
                },
            }
        )
        assert isinstance(manifest, Workflow)

    def test_workflow_template(self, stable_hooks):
        manifest = stable_hooks.parse_manifest(
            manifest={
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "WorkflowTemplate",
                "metadata": {"generateName": "hello-world-"},
                "spec": {
                    "entrypoint": "hello-world",
                    "templates": [
                        {
                            "name": "hello-world",
                            "container": {
                                "image": "busybox",
                                "command": ["echo"],
                                "args": ["hello world"],
                            },
                        }
                    ],
                },
            }
        )
        assert isinstance(manifest, WorkflowTemplate)


class TestAnalyze:
    @hookimpl
    def analyze_workflow(self):
        yield {"code": "T001", "loc": (), "msg": "analyze_workflow"}

    @hookimpl
    def analyze_template(self):
        yield {"code": "T002", "loc": (), "msg": "analyze_template"}

    @hookimpl
    def analyze_step(self):
        yield {"code": "T003", "loc": (), "msg": "analyze_step"}

    def test_workflow(self, plugin_manager):
        plugin_manager.register(self)

        manifest = Workflow.model_validate(
            {
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "Workflow",
                "metadata": {"generateName": "hello-world-"},
                "spec": {
                    "entrypoint": "hello-world",
                    "templates": [
                        {
                            "name": "hello-world",
                            "container": {
                                "image": "busybox",
                                "command": ["echo"],
                                "args": ["hello world"],
                            },
                        }
                    ],
                },
            }
        )

        diagnoses_generators = plugin_manager.hook.analyze(manifest=manifest)
        diagnoses = list(itertools.chain.from_iterable(diagnoses_generators))
        assert diagnoses == [
            {
                "code": "T001",
                "loc": (),
                "msg": "analyze_workflow",
            },
            {
                "code": "T002",
                "loc": ("spec", "templates", 0),
                "msg": "analyze_template",
            },
        ]

    def test_workflowtemplate(self, plugin_manager):
        plugin_manager.register(self)

        manifest = WorkflowTemplate.model_validate(
            {
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "WorkflowTemplate",
                "metadata": {"name": "test"},
                "spec": {
                    "templates": [
                        {
                            "name": "hello-hello-hello",
                            "steps": [
                                [
                                    {
                                        "name": "hello1",
                                        "template": "print-message",
                                        "arguments": {
                                            "parameters": [
                                                {
                                                    "name": "message",
                                                    "value": "hello1",
                                                }
                                            ]
                                        },
                                    }
                                ],
                            ],
                        },
                        {
                            "name": "print-message",
                            "inputs": {"parameters": [{"name": "message"}]},
                            "container": {
                                "image": "busybox",
                                "command": ["echo"],
                                "args": ["{{inputs.parameters.message}}"],
                            },
                        },
                    ],
                },
            }
        )

        diagnoses_generators = plugin_manager.hook.analyze(manifest=manifest)
        diagnoses = list(itertools.chain.from_iterable(diagnoses_generators))
        assert diagnoses == [
            {
                "code": "T002",
                "loc": ("spec", "templates", 0),
                "msg": "analyze_template",
            },
            {
                "code": "T003",
                "loc": ("spec", "templates", 0, "steps", 0, 0),
                "msg": "analyze_step",
            },
            {
                "code": "T002",
                "loc": ("spec", "templates", 1),
                "msg": "analyze_template",
            },
        ]


class TestRules:
    def test_check_metadata_1(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_MALFORMED_NAME)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert (
            IsPartialDict(
                {"code": "M010", "loc": ("metadata", "name"), "fix": "invalid-name"}
            )
            in diagnoses
        )

    def test_check_metadata_2(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_MALFORMED_GENERATE_NAME)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert (
            IsPartialDict({"code": "M010", "loc": ("metadata", "generateName")})
            in diagnoses
        )

    def test_check_spec_1(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_MALFORMED_NAME)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert (
            IsPartialDict({"code": "M006", "loc": ("spec", "workflowTemplateRef")})
            in diagnoses
        )

    def test_check_spec_2(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_MALFORMED_GENERATE_NAME)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert (
            IsPartialDict({"code": "M004", "loc": ("spec", "entrypoint")}) in diagnoses
        )

    def test_check_entrypoint(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_ENTRYPOINT)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert (
            IsPartialDict({"code": "WF001", "loc": ("spec", "entrypoint")}) in diagnoses
        )
        assert (
            IsPartialDict({"code": "TPL001", "loc": ("spec", "templates", 0)})
            in diagnoses
        )
        assert (
            IsPartialDict({"code": "TPL001", "loc": ("spec", "templates", 2)})
            in diagnoses
        )

    def test_check_argument_parameters(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_MALFORMED_ARGUMENTS)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))
        assert (
            IsPartialDict(
                {"code": "WF002", "loc": ("spec", "arguments", "parameters", 0)}
            )
            in diagnoses
        )
        assert (
            IsPartialDict(
                {"code": "WF002", "loc": ("spec", "arguments", "parameters", 1)}
            )
            in diagnoses
        )
        assert (
            IsPartialDict(
                {
                    "code": "M005",
                    "loc": ("spec", "arguments", "parameters", 1, "default"),
                }
            )
            in diagnoses
        )

    def test_check_argument_artifacts(self):
        diagnoses = tugboat.analyze.analyze_yaml(MANIFEST_MALFORMED_ARGUMENTS)
        logger.critical("Diagnoses: %s", json.dumps(diagnoses, indent=2))

        assert (
            IsPartialDict(
                {
                    "code": "M006",
                    "loc": ("spec", "arguments", "artifacts", 1, "raw"),
                }
            )
            in diagnoses
        )
        assert (
            IsPartialDict(
                {
                    "code": "M006",
                    "loc": ("spec", "arguments", "artifacts", 1, "s3"),
                }
            )
            in diagnoses
        )

        assert (
            IsPartialDict(
                {"code": "WF003", "loc": ("spec", "arguments", "artifacts", 0)}
            )
            in diagnoses
        )
        assert (
            IsPartialDict(
                {"code": "WF003", "loc": ("spec", "arguments", "artifacts", 1)}
            )
            in diagnoses
        )


MANIFEST_MALFORMED_NAME = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  name: invalid_name  # M009
spec:
  templates: []
  workflowTemplateRef:  # M006
    name: test
"""


MANIFEST_MALFORMED_GENERATE_NAME = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: invalid_name_  # M010
spec:
  templates: []
"""


MANIFEST_INVALID_ENTRYPOINT = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  name: test
spec:
  entrypoint: main  # WT001
  templates:
    - name: hello  # TPL001
      container:
        image: busybox
    - name: world
      container:
        image: busybox
    - name: hello  # TPL001
      container:
        image: busybox
"""


MANIFEST_MALFORMED_ARGUMENTS = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  arguments:
    parameters:
      - name: message  # WT002
        valueFrom:
          configMapKeyRef:
            name: my-config
            key: my-key
      - name: message  # WT002
        default: foo
    artifacts:
      - name: data  # WT003
        raw:
          data: hello
      - name: data  # WT003
        raw:  # M006
          data: world
        s3:  # M006
          key: my-file
"""
