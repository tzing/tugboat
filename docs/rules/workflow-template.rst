Workflow Template Rules (``WT``)
================================

Code ``WT`` is used for errors specifically related to the `Workflow Template`_.
These errors are likely to cause runtime issues when the workflow template is used in a workflow.

.. _Workflow Template: https://argo-workflows.readthedocs.io/en/latest/workflow-templates/


.. WT0xx general issues

.. rule:: WT001 Use strict name

   This error occurs when a workflow template uses the ``metadata.generateName`` field instead of the ``metadata.name`` field.

   While Argo Workflows does not strictly enforce this, it is recommended to use the ``metadata.name`` field for workflow templates.
   This is because the workflow template will be referenced by its name in the workflow, and a randomly generated name can be difficult to remember.

   .. code-block:: yaml
      :emphasize-lines: 4

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        generateName: demo-
      spec:
        templates: []


.. WT1xx duplicated items

.. rule:: WT101 Duplicate parameter names

   The workflow template contains multiple input parameters (``.spec.arguments.parameters``) with the same name.

   In the following example, the template ``message`` is duplicated:

   .. code-block:: yaml
      :emphasize-lines: 8,10

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        name: demo
      spec:
        arguments:
          parameters:
            - name: message
              value: "Hello, World!"
            - name: message
              value: "Hello, Tugboat!"

.. rule:: WT102 Duplicate artifact names

   The workflow template contains multiple input artifacts (``.spec.arguments.artifacts``) with the same name.

   In the following example, the artifact ``message`` is duplicated:

   .. code-block:: yaml
      :emphasize-lines: 8,11

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        name: demo
      spec:
        arguments:
          artifacts:
            - name: message
              raw:
                 data: "Hello, World!"
            - name: message
              raw:
                 data: >-
                   Hello, Tugboat!


.. WT2xx reference issues

.. rule:: WT201 Invalid entrypoint

   The specified entrypoint does not exist in the workflow template.

   For instance, the following workflow specifies an entrypoint that does not exist:

   .. code-block:: yaml
      :emphasize-lines: 6

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        name: demo
      spec:
        entrypoint: non-existent
        templates:
          - name: hello
            container:
              image: alpine:latest

.. WT3xx field value issues

.. rule:: WT301 Invalid metric name

   This rule is triggered when a metric name in a template is invalid.

   Argo Workflows provides metrics in both `Prometheus`_ and `OpenTelemetry`_ formats.
   As a result, it must comply with the naming rules of both formats.
   This means metric names must begin with a letter and can only contain letters, numbers, and underscores (``_``).

   .. code-block:: yaml
      :emphasize-lines: 8

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        name: demo
      spec:
        metrics:
          prometheus:
            - name: invalid-metric-name
              help: This is an invalid metric name
              counter:
                value: "1"

   .. _Prometheus: https://prometheus.io/
   .. _OpenTelemetry: https://opentelemetry.io/

.. rule:: WT302 Invalid metric label name

   This rule is triggered when a metric label name in a template is invalid.

   Prometheus label names must start with an alphabetic character and can only contain alphanumeric characters and underscores (``_``).

   .. code-block:: yaml
      :emphasize-lines: 11

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        name: demo
      spec:
        metrics:
          prometheus:
            - name: demo_count
              help: This is an invalid metric name
              labels:
                - key: invalid-label-name
                  value: demo_value
              counter:
                value: "1"

.. rule:: WT303 Redundant metric label

   Prometheus metric labels with an empty value are treated the same as labels that are not defined.
   This rule is triggered when a metric label in a template has an empty value.

   .. code-block:: yaml
      :emphasize-lines: 12

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        name: demo
      spec:
        metrics:
          prometheus:
            - name: demo_count
              help: This is an invalid metric name
              labels:
                - key: demo_label
                  value: ""
              counter:
                value: "1"
