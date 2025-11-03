from tests.dirty_equals import HasSubstring, IsPartialModel
from tugboat.engine import analyze_yaml_stream


class TestGeneralRules:

    def test_analyze_template(self, diagnoses_logger):
        diagnoses = analyze_yaml_stream(MANIFEST_AMBIGUOUS_TYPE)
        diagnoses_logger(diagnoses)
        assert (
            IsPartialModel(
                {
                    "code": "M201",
                    "loc": ("spec", "templates", 0, "container"),
                }
            )
            in diagnoses
        )
        assert (
            IsPartialModel(
                {
                    "code": "M201",
                    "loc": ("spec", "templates", 0, "script"),
                }
            )
            in diagnoses
        )

    def test_check_field_references(self, diagnoses_logger):
        diagnoses = analyze_yaml_stream(MANIFEST_INVALID_REFERENCES)
        diagnoses_logger(diagnoses)
        assert (
            IsPartialModel(
                {
                    "code": "VAR002",
                    "loc": ("spec", "templates", 0, "container", "args", 1),
                    "msg": "The parameter reference 'inputs.parameters.command' used in template 'container-template' is invalid.",
                    "fix": "{{ inputs.parameters.cmd }}",
                }
            )
            in diagnoses
        )
        assert (
            IsPartialModel(
                {
                    "code": "VAR002",
                    "loc": ("spec", "templates", 1, "script", "source"),
                    "msg": "The parameter reference 'inputs.artifacts.data' used in template 'script-template' is invalid.",
                    "fix": "{{ inputs.artifacts.data.path }}",
                }
            )
            in diagnoses
        )

    def test_check_duplicate_step_names(self, diagnoses_logger):
        diagnoses = analyze_yaml_stream(MANIFEST_DUPLICATE_STEP_NAMES)
        diagnoses_logger(diagnoses)
        assert (
            IsPartialModel(
                {
                    "code": "STP101",
                    "loc": ("spec", "templates", 0, "steps", 0, 0, "name"),
                }
            )
            in diagnoses
        )
        assert (
            IsPartialModel(
                {
                    "code": "STP101",
                    "loc": ("spec", "templates", 0, "steps", 1, 0, "name"),
                }
            )
            in diagnoses
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


MANIFEST_INVALID_REFERENCES = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  entrypoint: container-template
  templates:
    - name: container-template
      inputs:
        parameters:
          - name: cmd
      container:
        image: python:alpine3.13
        command: [ python ]
        args:
          - -c
          - '{{ inputs.parameters.command }}'  # VAR002
    - name: script-template
      inputs:
        artifacts:
          - name: data
      script:
        image: python:alpine3.13
        command: [ python ]
        source: |-
          print('Hello world, {{ inputs.artifacts.data }}!')  # VAR002
"""

MANIFEST_DUPLICATE_STEP_NAMES = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: steps-
spec:
  entrypoint: hello-hello
  templates:
    - name: hello-hello
      steps:
        - - name: hello
            #     ^^^^^ This step is duplicated
            template: print-message
            arguments:
              parameters:
                - name: message
                  value: "hello-1"
        - - name: hello
            #     ^^^^^ This step is duplicated
            template: print-message
            arguments:
              parameters:
                - name: message
                  value: "hello-2"
"""


def test_check_input_parameters_1(diagnoses_logger):
    diagnoses = analyze_yaml_stream(MANIFEST_INVALID_INPUT_PARAMETERS)
    diagnoses_logger(diagnoses)
    assert (
        IsPartialModel(
            {
                "code": "TPL102",
                "loc": ("spec", "templates", 0, "inputs", "parameters", 0, "name"),
            }
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            {
                "code": "TPL102",
                "loc": ("spec", "templates", 0, "inputs", "parameters", 1, "name"),
            }
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            {
                "code": "M102",
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
        in diagnoses
    )
    assert (
        IsPartialModel(
            {
                "code": "VAR001",
                "loc": ("spec", "templates", 0, "inputs", "parameters", 1, "value"),
            }
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            {
                "code": "TPL201",
                "loc": ("spec", "templates", 0, "inputs", "parameters", 2, "value"),
                "msg": "The parameter reference 'workflow.invalid' used in parameter 'message-3' is invalid.",
                "input": "{{ workflow.invalid}}",
            }
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            {
                "code": "M103",
                "loc": ("spec", "templates", 0, "inputs", "parameters", 3, "value"),
            }
        )
        in diagnoses
    )


MANIFEST_INVALID_INPUT_PARAMETERS = """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  entrypoint: test
  templates:
    - name: main
      inputs:
        parameters:
          - name: message # TPL102
            valueFrom:
              path: /malformed # M102
          - name: message # TPL102
            value: "{{ workflow.name " # VAR001
          - name: message-3
            value: "{{ workflow.invalid}}" #
          - name: message-4
            value:
              foo: bar # M103
"""


def test_check_input_parameters_2(diagnoses_logger):
    diagnoses = analyze_yaml_stream(
        """
        apiVersion: argoproj.io/v1alpha1
        kind: WorkflowTemplate
        metadata:
          name: test
        spec:
          templates:
            - name: main
              inputs:
                parameters:
                  - name: message
                    value: foobar  # M102
        """
    )
    diagnoses_logger(diagnoses)
    assert (
        IsPartialModel(
            {
                "code": "M102",
                "loc": ("spec", "templates", 0, "inputs", "parameters", 0, "value"),
            }
        )
        in diagnoses
    )


def test_check_input_artifacts(diagnoses_logger):
    diagnoses = analyze_yaml_stream(
        """
        apiVersion: argoproj.io/v1alpha1
        kind: Workflow
        metadata:
          generateName: test-
        spec:
          entrypoint: test
          templates:
            - name: test
              inputs:
                artifacts:
                  - name: data # TPL103
                    raw:
                      data:
                        This is a message from {{ workflow.namee }}. # TPL202
                  - name: data # TPL103
                    value: foo # M102
              container:
                image: alpine:latest
        """
    )
    diagnoses_logger(diagnoses)

    # 0-th template
    loc = ("spec", "templates", 0, "inputs", "artifacts")

    # TPL103: duplicate artifact names
    assert IsPartialModel(code="TPL103", loc=(*loc, 0, "name")) in diagnoses
    assert IsPartialModel(code="TPL103", loc=(*loc, 1, "name")) in diagnoses

    # TPL202: improper use of raw artifact field
    assert (
        IsPartialModel(
            code="TPL202",
            loc=(*loc, 0, "raw", "data"),
            msg=HasSubstring(
                "The parameter reference 'workflow.namee' used in artifact 'data' is invalid."
            ),
            fix="{{ workflow.name }}",
        )
        in diagnoses
    )

    # M102: invalid fields
    assert IsPartialModel(code="M102", loc=(*loc, 1, "value")) in diagnoses


def test_check_output_parameters(diagnoses_logger):
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
              container:
                image: busybox:latest
              outputs:
                parameters:
                  - name: message # TPL104
                  - name: message # TPL104
                    valueFrom:
                      parameter: "{{ workflow.invalid}}" # VAR002
        """
    )
    diagnoses_logger(diagnoses)

    loc = ("spec", "templates", 0, "outputs", "parameters")
    assert IsPartialModel(code="TPL104", loc=(*loc, 0, "name")) in diagnoses
    assert IsPartialModel(code="TPL104", loc=(*loc, 1, "name")) in diagnoses

    assert IsPartialModel(code="M101", loc=(*loc, 0, "valueFrom")) in diagnoses
    assert (
        IsPartialModel(code="VAR002", loc=(*loc, 1, "valueFrom", "parameter"))
        in diagnoses
    )


def test_check_output_artifacts(diagnoses_logger):
    diagnoses = analyze_yaml_stream(
        """
        apiVersion: argoproj.io/v1alpha1
        kind: Workflow
        metadata:
          generateName: test-
        spec:
          templates:
            - name: main
              outputs:
                artifacts:
                  - name: data # TPL105
                    path: /data
                    archive: {} # M101
                  - name: data # TPL105
                    from: '{{ invalid }}'
        """
    )
    diagnoses_logger(diagnoses)

    loc = ("spec", "templates", 0, "outputs", "artifacts")
    assert IsPartialModel(code="TPL105", loc=(*loc, 0, "name")) in diagnoses
    assert IsPartialModel(code="TPL105", loc=(*loc, 1, "name")) in diagnoses

    assert IsPartialModel(code="M101", loc=(*loc, 0, "archive")) in diagnoses
    assert IsPartialModel(code="VAR002", loc=(*loc, 1, "from")) in diagnoses


def test_check_metrics(diagnoses_logger):
    diagnoses = analyze_yaml_stream(
        """
        apiVersion: argoproj.io/v1alpha1
        kind: Workflow
        metadata:
          generateName: test-
        spec:
          templates:
            - name: template-1
              inputs:
                parameters:
                  - name: in-param
                    value: "value-1"
              outputs:
                parameters:
                  - name: out-param
                    valueFrom:
                      path: /tmp/param-2
              metrics:
               prometheus:
                - name: metric-1 # TPL301
                  help: this is a demo
                  labels:
                    - key: invalid-label
                      value: ""
                  counter:
                    value: "{{ outputs.parameters.no-param }}" # VAR002
        """
    )
    diagnoses_logger(diagnoses)

    assert (
        IsPartialModel(
            {
                "code": "TPL301",
                "loc": ("spec", "templates", 0, "metrics", "prometheus", 0, "name"),
            }
        )
        in diagnoses
    )

    loc_labels = ("spec", "templates", 0, "metrics", "prometheus", 0, "labels")
    assert (
        IsPartialModel(
            {
                "code": "TPL302",
                "loc": (*loc_labels, 0, "key"),
            }
        )
        in diagnoses
    )
    assert (
        IsPartialModel(
            {
                "code": "TPL303",
                "loc": (*loc_labels, 0, "value"),
            }
        )
        in diagnoses
    )

    assert (
        IsPartialModel(
            {
                "code": "VAR002",
                "loc": (
                    "spec",
                    "templates",
                    0,
                    "metrics",
                    "prometheus",
                    0,
                    "counter",
                    "value",
                ),
            }
        )
        in diagnoses
    )
