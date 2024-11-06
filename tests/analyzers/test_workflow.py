import json
import logging

import ruamel.yaml
from dirty_equals import IsPartialDict

import tugboat.analyze
from tests.utils import ContainsSubStrings
from tugboat.core import hookimpl
from tugboat.schemas import Workflow, WorkflowTemplate

logger = logging.getLogger(__name__)
yaml = ruamel.yaml.YAML(typ="safe")


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

        diagnostics = list(plugin_manager.hook.analyze(manifest=manifest))
        assert diagnostics == [
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
                "metadata": {"generateName": "steps-"},
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

        diagnostics = list(plugin_manager.hook.analyze(manifest=manifest))
        assert diagnostics == [
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
    def test_check_manifest(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_SPEC_MUTUALLY_EXCLUSIVE)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert IsPartialDict({"code": "M006"}) in diagnostics
        assert IsPartialDict({"code": "M010", "fix": "test-workflow-"}) in diagnostics

    def test_check_entrypoint(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_MISSING_ENTRYPOINT)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert IsPartialDict({"code": "M004"}) in diagnostics
        assert IsPartialDict({"code": "M010"}) in diagnostics

    def test_check_entrypoint_exists(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_ENTRYPOINT)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert (
            IsPartialDict(
                {
                    "code": "WF001",
                    "msg": ContainsSubStrings(
                        "Entrypoint 'main' is not defined in any template.",
                        "Defined entrypoints: 'hello' and 'world'.",
                    ),
                }
            )
            in diagnostics
        )

    def test_check_workflow_argument_parameters(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_ENTRYPOINT)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert (
            IsPartialDict(
                {
                    "code": "M005",
                    "loc": ("spec", "arguments", "parameters", 0, "default"),
                }
            )
            in diagnostics
        )
        assert (
            IsPartialDict(
                {
                    "code": "M006",
                    "loc": ("spec", "arguments", "parameters", 0, "valueFrom"),
                }
            )
            in diagnostics
        )

    def test_check_workflow_argument_parameter_names(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_MALFORMED_ARGUMENTS)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert (
            IsPartialDict(
                {"code": "WF003", "loc": ("spec", "arguments", "parameters", 0)}
            )
            in diagnostics
        )
        assert (
            IsPartialDict(
                {"code": "WF003", "loc": ("spec", "arguments", "parameters", 1)}
            )
            in diagnostics
        )

    def test_check_template_names(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_DUPLICATED_TEMPLATE_NAMES)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert (
            IsPartialDict({"code": "M004", "loc": ("spec", "templates", 3)})
            in diagnostics
        )
        assert (
            IsPartialDict({"code": "WF002", "loc": ("spec", "templates", 0)})
            in diagnostics
        )
        assert (
            IsPartialDict({"code": "WF002", "loc": ("spec", "templates", 2)})
            in diagnostics
        )

    def test_check_workflow_argument_artifacts(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_MALFORMED_ARGUMENTS)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert (
            IsPartialDict(
                {
                    "code": "M006",
                    "loc": ("spec", "arguments", "artifacts", 1, "raw"),
                }
            )
            in diagnostics
        )
        assert (
            IsPartialDict(
                {
                    "code": "M006",
                    "loc": ("spec", "arguments", "artifacts", 1, "s3"),
                }
            )
            in diagnostics
        )

    def test_check_workflow_argument_artifact_names(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_MALFORMED_ARGUMENTS)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert (
            IsPartialDict(
                {"code": "WF004", "loc": ("spec", "arguments", "artifacts", 0)}
            )
            in diagnostics
        )
        assert (
            IsPartialDict(
                {"code": "WF004", "loc": ("spec", "arguments", "artifacts", 1)}
            )
            in diagnostics
        )


MANIFEST_SPEC_MUTUALLY_EXCLUSIVE = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test_workflow-  # <-- M010
spec:
  templates:
    - name: main
      container:
        image: busybox
  workflowTemplateRef:
    name: test
"""

MANIFEST_MISSING_ENTRYPOINT = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  name: test_workflow  # <-- M010
spec:
  templates:
    - name: main
      container:
        image: busybox
"""

MANIFEST_INVALID_ENTRYPOINT = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  entrypoint: main  # <-- WF001
  templates:
    - name: hello
      container:
        image: busybox
    - name: world
      container:
        image: busybox
  arguments:
    parameters:
      - name: message-1
        value: hello
        default: world  # <-- M005
        valueFrom: # <-- M006
          configMapKeyRef:
            name: test-config
            key: key
"""

MANIFEST_DUPLICATED_TEMPLATE_NAMES = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  entrypoint: hello
  templates:
    - name: hello  # <-- WF002
      container:
        image: busybox
    - name: world
      container:
        image: busybox
    - name: hello  # <-- WF002
      container:
        image: busybox
    - container:  # <-- M004
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
      - name: message  # <-- WF003
      - name: message  # <-- WF003
    artifacts:
      - name: data  # <-- WF004
        raw:
          data: hello
      - name: data  # <-- WF004
        raw:  # <-- M006
          data: world
        s3:  # <-- M006
          key: my-file
"""
