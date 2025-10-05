import itertools

from tugboat.core import hookimpl
from tugboat.engine import analyze_yaml_stream
from tugboat.schemas import Workflow, WorkflowTemplate
from tests.dirty_equals import IsPartialModel


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
    def test_check_metadata_1(self, diagnoses_logger):
        diagnoses = analyze_yaml_stream(MANIFEST_MALFORMED_NAME)
        diagnoses_logger(diagnoses)
        assert (
            IsPartialModel(
                {"code": "M301", "loc": ("metadata", "name"), "fix": "invalid-name"}
            )
            in diagnoses
        )

    def test_check_metadata_2(self, diagnoses_logger):
        diagnoses = analyze_yaml_stream(MANIFEST_MALFORMED_GENERATE_NAME)
        diagnoses_logger(diagnoses)
        assert (
            IsPartialModel({"code": "M301", "loc": ("metadata", "generateName")})
            in diagnoses
        )

    def test_check_spec_1(self, diagnoses_logger):
        diagnoses = analyze_yaml_stream(MANIFEST_MALFORMED_NAME)
        diagnoses_logger(diagnoses)
        assert (
            IsPartialModel({"code": "M201", "loc": ("spec", "workflowTemplateRef")})
            in diagnoses
        )

    def test_check_spec_2(self, diagnoses_logger):
        diagnoses = analyze_yaml_stream(MANIFEST_MALFORMED_GENERATE_NAME)
        diagnoses_logger(diagnoses)
        assert (
            IsPartialModel({"code": "M101", "loc": ("spec", "entrypoint")})
            in diagnoses
        )

    def test_check_entrypoint(self, diagnoses_logger):
        diagnoses = analyze_yaml_stream(MANIFEST_INVALID_ENTRYPOINT)
        diagnoses_logger(diagnoses)
        assert (
            IsPartialModel({"code": "WF201", "loc": ("spec", "entrypoint")}) in diagnoses
        )
        assert (
            IsPartialModel({"code": "TPL101", "loc": ("spec", "templates", 0, "name")})
            in diagnoses
        )
        assert (
            IsPartialModel({"code": "TPL101", "loc": ("spec", "templates", 2, "name")})
            in diagnoses
        )

    def test_check_argument_parameters(self, diagnoses_logger):
        diagnoses = analyze_yaml_stream(MANIFEST_MALFORMED_ARGUMENTS)
        diagnoses_logger(diagnoses)
        assert (
            IsPartialModel(
                {"code": "WF101", "loc": ("spec", "arguments", "parameters", 0, "name")}
            )
            in diagnoses
        )
        assert (
            IsPartialModel(
                {"code": "WF101", "loc": ("spec", "arguments", "parameters", 1, "name")}
            )
            in diagnoses
        )
        assert (
            IsPartialModel(
                {
                    "code": "M102",
                    "loc": ("spec", "arguments", "parameters", 1, "default"),
                }
            )
            in diagnoses
        )

    def test_check_argument_artifacts(self, diagnoses_logger):
        diagnoses = analyze_yaml_stream(MANIFEST_MALFORMED_ARGUMENTS)
        diagnoses_logger(diagnoses)

        assert (
            IsPartialModel(
                {
                    "code": "M201",
                    "loc": ("spec", "arguments", "artifacts", 1, "raw"),
                }
            )
            in diagnoses
        )
        assert (
            IsPartialModel(
                {
                    "code": "M201",
                    "loc": ("spec", "arguments", "artifacts", 1, "s3"),
                }
            )
            in diagnoses
        )

        assert (
            IsPartialModel(
                {"code": "WF102", "loc": ("spec", "arguments", "artifacts", 0, "name")}
            )
            in diagnoses
        )
        assert (
            IsPartialModel(
                {"code": "WF102", "loc": ("spec", "arguments", "artifacts", 1, "name")}
            )
            in diagnoses
        )


MANIFEST_MALFORMED_NAME = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  name: invalid_name  # M302
spec:
  templates: []
  workflowTemplateRef:  # M201
    name: test
"""


MANIFEST_MALFORMED_GENERATE_NAME = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: invalid_name_  # M301
spec:
  templates: []
"""


MANIFEST_INVALID_ENTRYPOINT = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
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


MANIFEST_MALFORMED_ARGUMENTS = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
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
        raw:
          data: hello
      - name: data  # WT102
        raw:  # M201
          data: world
        s3:  # M201
          key: my-file
"""


def test_check_metrics(diagnoses_logger):
    diagnoses = analyze_yaml_stream(
        """
        apiVersion: argoproj.io/v1alpha1
        kind: Workflow
        metadata:
          generateName: test-
        spec:
          metrics:
            prometheus:
              - name: metric-1 # WF301
                help: this is a demo
                labels:
                  - key: invalid-label
                    value: ""
                counter:
                  value: "1"
        """
    )
    diagnoses_logger(diagnoses)

    assert (
        IsPartialModel(
            {
                "code": "WF301",
                "loc": ("spec", "metrics", "prometheus", 0, "name"),
            }
        )
        in diagnoses
    )

    loc_labels = ("spec", "metrics", "prometheus", 0, "labels")
    assert (
        IsPartialModel(
            {
                "code": "WF302",
                "loc": (*loc_labels, 0, "key"),
            }
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            {
                "code": "WF303",
                "loc": (*loc_labels, 0, "value"),
            }
        )
        in diagnoses
    )
