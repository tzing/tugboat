Workflow Rules (``WF``)
=======================

Code ``WF`` is used for issues closely related to the `Workflow`_.
These issues are likely to cause runtime errors when the workflow is executed.

.. _Workflow: https://argo-workflows.readthedocs.io/en/latest/workflow-concepts/#the-workflow


.. WF1xx duplicated items

.. rule:: WF101 Duplicated parameter name

   The workflow contains multiple input parameters (``.spec.arguments.parameters``) with the same name.

   In the following example, the template ``message`` is duplicated:

   .. code-block:: yaml
      :emphasize-lines: 8,10

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        generateName: hello-
      spec:
        arguments:
          parameters:
            - name: message
              value: "Hello, World!"
            - name: message
              value: "Hello, Tugboat!"

.. rule:: WF102 Duplicated artifact name

   The workflow contains multiple input artifacts (``.spec.arguments.artifacts``) with the same name.

   In the following example, the artifact ``message`` is duplicated:

   .. code-block:: yaml
      :emphasize-lines: 8,11

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        generateName: hello-
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


.. WF2xx reference issues

.. rule:: WF201 Invalid entrypoint

   The specified entrypoint does not exist in the workflow.

   For instance, the following workflow specifies an entrypoint that does not exist:

   .. code-block:: yaml
      :emphasize-lines: 6

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        generateName: hello-
      spec:
        entrypoint: non-existent
        templates:
          - name: hello
            container:
              image: alpine:latest

.. WF3xx field value issues

.. rule:: WF301 Invalid metric name

   This rule is triggered when a metric name in a template is invalid.

   The metric name is used as the identifier for the metric in the `Prometheus`_ server.
   As a result, it must follow the naming conventions for Prometheus metrics.

   A valid metric name must start with an alphabetic character and can only include alphanumeric characters, underscores (``_``), and colons (``:``). For more details, refer to the `Prometheus documentation`_.

   .. code-block:: yaml
      :emphasize-lines: 8

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        generateName: demo-
      spec:
        metrics:
          prometheus:
            - name: invalid-metric-name
              help: This is an invalid metric name
              counter:
                value: "1"

   .. _Prometheus: https://prometheus.io/
   .. _Prometheus documentation: https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels

.. rule:: WF302 Invalid metric label name

   This rule is triggered when a metric label name in a template is invalid.

   Prometheus label names must start with an alphabetic character and can only contain alphanumeric characters and underscores (``_``). See `Prometheus documentation`_ for more details.

   .. code-block:: yaml
      :emphasize-lines: 11

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        generateName: demo-
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

.. rule:: WF303 Redundant metric label

   Prometheus metric labels with an empty value are treated the same as labels that are not defined.
   This rule is triggered when a metric label in a template has an empty value.

   .. code-block:: yaml
      :emphasize-lines: 12

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        generateName: demo-
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
