from tests.dirty_equals import IsPartialModel
from tugboat.engine import analyze_yaml_stream


class TestRules:
    def test_check_metadata_1(self, diagnoses_logger):
        diagnoses = analyze_yaml_stream(MANIFEST_NAME_TOO_LONG)
        diagnoses_logger(diagnoses)
        assert IsPartialModel({"code": "M302"}) in diagnoses

    def test_check_metadata_2(self, diagnoses_logger):
        diagnoses = analyze_yaml_stream(MANIFEST_USE_GENERATE_NAME)
        diagnoses_logger(diagnoses)
        assert IsPartialModel({"code": "WT001"}) in diagnoses

    def test_check_spec(self, diagnoses_logger):
        diagnoses = analyze_yaml_stream(MANIFEST_USE_GENERATE_NAME)
        diagnoses_logger(diagnoses)
        assert IsPartialModel({"code": "M201"}) in diagnoses

    def test_check_entrypoint(self, diagnoses_logger):
        diagnoses = analyze_yaml_stream(MANIFEST_INVALID_ENTRYPOINT)
        diagnoses_logger(diagnoses)
        assert IsPartialModel({"code": "WT201"}) in diagnoses
        assert IsPartialModel({"code": "TPL101"}) in diagnoses


MANIFEST_NAME_TOO_LONG = """
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  name: a-very-long-name-that-is-definitely-too-long-for-argo-workflow-templates  # WT201
spec:
  templates: []
"""


MANIFEST_USE_GENERATE_NAME = """
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  generateName: test-workflow-  # WT201
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


def test_check_argument_parameters(diagnoses_logger):
    diagnoses = analyze_yaml_stream(MANIFEST_MALFORMED_PARAMETERS)
    diagnoses_logger(diagnoses)

    # WT101: Duplicated parameter name
    assert (
        IsPartialModel(
            {"code": "WT101", "loc": ("spec", "arguments", "parameters", 0, "name")}
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            {"code": "WT101", "loc": ("spec", "arguments", "parameters", 1, "name")}
        )
        in diagnoses
    )

    # M103: Type error
    assert (
        IsPartialModel(
            {"code": "M103", "loc": ("spec", "arguments", "parameters", 2, "value")}
        )
        in diagnoses
    )


MANIFEST_MALFORMED_PARAMETERS = """
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
      - name: param-3
        value:
          foo: bar # M103
"""


def test_check_argument_artifacts(diagnoses_logger):
    diagnoses = analyze_yaml_stream(
        """
        apiVersion: argoproj.io/v1alpha1
        kind: WorkflowTemplate
        metadata:
          name: test
        spec:
          arguments:
            artifacts:
              - name: data  # WT102
                raw:  # M201
                  data: world
                s3:  # M201
                  key: my-file
              - name: data  # WT102
                raw:
                  data: hello
              - name: artifact-3
        """
    )
    diagnoses_logger(diagnoses)

    # WT102: Duplicated input artifact name
    assert (
        IsPartialModel(
            {"code": "WT102", "loc": ("spec", "arguments", "artifacts", 0, "name")}
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            {"code": "WT102", "loc": ("spec", "arguments", "artifacts", 1, "name")}
        )
        in diagnoses
    )

    # M201: Invalid reference
    assert (
        IsPartialModel(
            {
                "code": "M201",
                "loc": ("spec", "arguments", "artifacts", 0, "raw"),
            }
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            {
                "code": "M201",
                "loc": ("spec", "arguments", "artifacts", 0, "s3"),
            }
        )
        in diagnoses
    )


def test_check_metrics(diagnoses_logger):
    diagnoses = analyze_yaml_stream(
        """
        apiVersion: argoproj.io/v1alpha1
        kind: WorkflowTemplate
        metadata:
          name: test
        spec:
          metrics:
            prometheus:
              - name: metric-1 # WT301
                help: this is a demo
                labels:
                  - key: invalid-label # WT302
                    value: "" # WT303
                counter:
                  value: "1"
        """
    )
    diagnoses_logger(diagnoses)

    assert (
        IsPartialModel(
            {
                "code": "WT301",
                "loc": ("spec", "metrics", "prometheus", 0, "name"),
            }
        )
        in diagnoses
    )

    loc_labels = ("spec", "metrics", "prometheus", 0, "labels")
    assert (
        IsPartialModel(
            {
                "code": "WT302",
                "loc": (*loc_labels, 0, "key"),
            }
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            {
                "code": "WT303",
                "loc": (*loc_labels, 0, "value"),
            }
        )
        in diagnoses
    )
