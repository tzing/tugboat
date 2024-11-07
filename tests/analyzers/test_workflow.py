import json
import logging

import ruamel.yaml
from dirty_equals import IsPartialDict

import tugboat.analyze
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
    def test_check_metadata_1(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_MALFORMED_NAME)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert (
            IsPartialDict(
                {"code": "M010", "loc": ("metadata", "name"), "fix": "invalid-name"}
            )
            in diagnostics
        )

    def test_check_metadata_2(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_MALFORMED_GENERATE_NAME)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert (
            IsPartialDict({"code": "M010", "loc": ("metadata", "generateName")})
            in diagnostics
        )

    def test_check_spec_1(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_MALFORMED_NAME)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert (
            IsPartialDict({"code": "M006", "loc": ("spec", "workflowTemplateRef")})
            in diagnostics
        )

    def test_check_spec_2(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_MALFORMED_GENERATE_NAME)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert (
            IsPartialDict({"code": "M004", "loc": ("spec", "entrypoint")})
            in diagnostics
        )

    def test_check_entrypoint(self):
        diagnostics = tugboat.analyze.analyze_yaml(MANIFEST_INVALID_ENTRYPOINT)
        logging.critical("Diagnostics: %s", json.dumps(diagnostics, indent=2))
        assert (
            IsPartialDict({"code": "WF001", "loc": ("spec", "entrypoint")})
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

    def test_check_argument_parameters(self):
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
        assert (
            IsPartialDict(
                {
                    "code": "M005",
                    "loc": ("spec", "arguments", "parameters", 1, "default"),
                }
            )
            in diagnostics
        )

    def test_check_argument_artifacts(self):
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
kind: Workflow
metadata:
  generateName: test-
spec:
  arguments:
    parameters:
      - name: message  # WF003
        valueFrom:
          configMapKeyRef:
            name: my-config
            key: my-key
      - name: message  # WF003
        default: foo
    artifacts:
      - name: data  # WF004
        raw:
          data: hello
      - name: data  # WF004
        raw:  # M006
          data: world
        s3:  # M006
          key: my-file
"""
