Template Rules (``TPL``)
========================

Code ``TPL`` is used for errors specifically related to `the template <https://argo-workflows.readthedocs.io/en/latest/fields/#template>`_, the reusable and composable unit of execution in a workflow or workflow template.

Coverage
--------

Argo Workflows offers various types of templates. However, Tugboat currently supports only a few of them:

.. list-table::
    :header-rows: 1

    * - Template Type
      - Schema Validation [#schm-chk]_
      - Static Analysis [#sttc-chk]_

    * - Container template
      - :octicon:`alert` Partial (:py:class:`~tugboat.schemas.ContainerTemplate`)
      - :octicon:`check`

    * - `Container set template <https://argo-workflows.readthedocs.io/en/latest/container-set-template/>`_
      - :octicon:`alert` Partial (:py:class:`~tugboat.schemas.template.container.ContainerSetTemplate`)
      - :octicon:`check`

    * - `DAG template <https://argo-workflows.readthedocs.io/en/latest/walk-through/dag/>`_
      - :octicon:`alert` Partial (:py:class:`~tugboat.schemas.DagTask`)
      - :octicon:`check` :doc:`dag`

    * - `Data template <https://argo-workflows.readthedocs.io/en/latest/data-sourcing-and-transformation/>`_
      - :octicon:`x`
      - :octicon:`x`

    * - `HTTP template <https://argo-workflows.readthedocs.io/en/latest/http-template/>`_
      - :octicon:`x`
      - :octicon:`x`

    * - `Resource template <https://argo-workflows.readthedocs.io/en/latest/walk-through/kubernetes-resources/>`_
      - :octicon:`x`
      - :octicon:`x`

    * - `Script template <https://argo-workflows.readthedocs.io/en/latest/walk-through/scripts-and-results/>`_
      - :octicon:`alert` Partial (:py:class:`~tugboat.schemas.ScriptTemplate`)
      - :octicon:`check`

    * - `Steps template <https://argo-workflows.readthedocs.io/en/latest/walk-through/steps/>`_
      - :octicon:`alert` Partial (:py:class:`~tugboat.schemas.Step`)
      - :octicon:`check` :doc:`step`

    * - `Suspend template <https://argo-workflows.readthedocs.io/en/latest/walk-through/suspending/>`_
      - :octicon:`check` (:py:class:`~tugboat.schemas.template.SuspendTemplate`)
      - :octicon:`x`

.. [#schm-chk] The schema validation phase checks the manifest against the schema defined in the official `field reference`_ document. It identifies missing or extra fields, incorrect data types, and other basic errors. These errors will be reported as :doc:`manifest-errors`.
.. [#sttc-chk] The static analysis examines the manifest's fields and values according to a set of expert rules. It detects unusual values, misused parameters, and potential runtime issues like duplicate names.
.. _Field Reference: https://argo-workflows.readthedocs.io/en/latest/fields/

Rules
-----

.. TPL1xx duplicated items

.. rule:: TPL101 Duplicate template names

   The workflow or workflow template contains multiple templates with the same name.

   In the following example, the template ``hello`` is duplicated:

   .. code-block:: yaml
      :emphasize-lines: 7,10

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        name: demo
      spec:
        templates:
          - name: hello
            container:
              image: alpine:latest
          - name: hello
            container:
              image: busybox:latest

.. rule:: TPL102 Duplicate input parameter names

   The template contains multiple input parameters (``<template>.inputs.parameters``) with the same name.

   .. code-block:: yaml
      :emphasize-lines: 10,11

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        name: demo
      spec:
        templates:
          - name: main
            inputs:
              parameters:
                - name: data
                - name: data
            ...

.. rule:: TPL103 Duplicate input artifact names

   The template contains multiple input artifacts (``<template>.inputs.artifacts``) with the same name.

   .. code-block:: yaml
      :emphasize-lines: 10,12

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        name: demo
      spec:
        templates:
          - name: main
            inputs:
              artifacts:
                - name: data
                  path: /data/foo
                - name: data
                  path: /data/bar
            ...

.. rule:: TPL104 Duplicate output parameter names

   The template contains multiple output parameters (``<template>.outputs.parameters``) with the same name.

   .. code-block:: yaml
      :emphasize-lines: 11,14

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        name: demo
      spec:
        templates:
           - name: main
             ...
             outputs:
               parameters:
                 - name: message
                   valueFrom:
                     path: /tmp/message.txt
                 - name: message
                   valueFrom:
                     path: /tmp/msg.txt

.. rule:: TPL105 Duplicate output artifact names

   The template contains multiple output artifacts (``<template>.outputs.artifacts``) with the same name.

   .. code-block:: yaml
      :emphasize-lines: 11,13

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        name: demo
      spec:
        templates:
           - name: main
             ...
             outputs:
               artifacts:
                 - name: data
                   path: /data/foo
                 - name: data
                   path: /data/bar


.. TPL2xx variable reference issues

.. rule:: TPL201 Invalid parameter reference

   Found invalid parameter reference in the template input parameter.

   This rule is a variation of :rule:`VAR002`.
   It is triggered when a template input parameter references an invalid objective:

   .. code-block:: yaml
      :emphasize-lines: 11

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        name: demo
      spec:
        templates:
          - name: main
            inputs:
              parameters:
                - name: data
                  value: "{{ inputs.parameters.invalid }}"

.. rule:: TPL202 Improper use of raw artifact field

   This rule is triggered when a raw artifact in the input arguments references something other than a parameter.
   Raw artifacts are designed to accept only parameter references, but users often mistakenly try to reference artifacts in this field.

   The purpose of this rule is to identify such cases where artifacts are incorrectly referenced.
   However, it is important to note that this rule is not limited to detecting artifact references - it also flags other types of invalid references that do not conform to the expected parameter format.

   For example, the following code demonstrates a scenario where this rule would be triggered:

   .. code-block:: yaml
      :emphasize-lines: 13

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        name: demo
      spec:
        templates:
          - name: main
            inputs:
              artifacts:
                - name: data
                  raw:
                    data: |-
                      {{ inputs.artifacts.any }}

.. TPL3xx field value issues

.. rule:: TPL301 Invalid metric name

   This rule is triggered when a metric name in a template is invalid.

   Argo Workflows provides metrics in both `Prometheus`_ and `OpenTelemetry`_ formats.
   As a result, it must comply with the naming rules of both formats.
   This means metric names must begin with a letter and can only contain letters, numbers, and underscores (``_``).

   .. code-block:: yaml
      :emphasize-lines: 13

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        name: demo
      spec:
        templates:
          - name: main
            container:
              image: alpine:latest
              command: ["true"]
            metrics:
              prometheus:
                - name: invalid-metric-name
                  help: This is an invalid metric name
                  counter:
                    value: "1"

   .. _Prometheus: https://prometheus.io/
   .. _OpenTelemetry: https://opentelemetry.io/

.. rule:: TPL302 Invalid metric label name

   This rule is triggered when a metric label name in a template is invalid.

   Prometheus label names must start with an alphabetic character and can only contain alphanumeric characters and underscores (``_``).

   .. code-block:: yaml
      :emphasize-lines: 16

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        name: demo
      spec:
        templates:
          - name: main
            container:
              image: alpine:latest
              command: ["true"]
            metrics:
              prometheus:
                - name: demo_count
                  help: This is an invalid metric name
                  labels:
                    - key: invalid-label-name
                      value: demo_value
                  counter:
                    value: "1"

.. rule:: TPL303 Redundant metric label

   Prometheus metric labels with an empty value are treated the same as labels that are not defined.
   This rule is triggered when a metric label in a template has an empty value.

   .. code-block:: yaml
      :emphasize-lines: 17

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        name: demo
      spec:
        templates:
          - name: main
            container:
              image: alpine:latest
              command: ["true"]
            metrics:
              prometheus:
                - name: demo_count
                  help: This is an invalid metric name
                  labels:
                    - key: demo_label
                      value: ""
                  counter:
                    value: "1"

.. rule:: TPL304 Request resource exceeds the limit

    This rule is triggered when a template's requests for resources (e.g., memory or CPU) are greater than the corresponding resource limits.

    The rule checks the resource ``requests`` in the template and compares them against the value from ``limits`` defined in the same template.
    If the requested resources exceed the defined limits, this rule is triggered.

    .. code-block:: yaml
        :emphasize-lines: 12-13

        apiVersion: argoproj.io/v1alpha1
        kind: WorkflowTemplate
        metadata:
          name: demo
        spec:
          templates:
            - name: main
              container:
                image: alpine:latest
                resources:
                  requests:
                    memory: 100Gi
                    cpu: "1.5"
                  limits:
                    memory: 10Gi
                    cpu: 1000m
