DAG Rules (``DAG``)
===================

Code ``DAG`` is used for errors related to the `DAG`_ in a `template`_.

.. _dag: https://argo-workflows.readthedocs.io/en/latest/walk-through/dag/
.. _template: https://argo-workflows.readthedocs.io/en/latest/fields/#template

.. DAG1xx duplicated items

.. rule:: DAG101 Duplicate task names

   The template contains multiple tasks with the same name.

   .. code-block:: yaml
      :emphasize-lines: 11,17

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        generateName: steps-
      spec:
        entrypoint: hello-hello
        templates:
          - name: hello-hello
            dag:
              tasks:
                - name: hello
                  template: print-message
                  arguments:
                    parameters:
                      - name: message
                        value: "hello-1"
                - name: hello
                  template: print-message
                  arguments:
                    parameters:
                      - name: message
                        value: "hello-2"

.. rule:: DAG102 Duplicate input parameters

   The task contains several input parameters (``<task>.arguments.parameters``) that share the same name,
   which means the parameter was set multiple times.

   .. code-block:: yaml
      :emphasize-lines: 15,17

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        name: test-
      spec:
        entrypoint: main
        templates:
          - name: main
            dag:
              tasks:
                - name: hello
                  template: print-message
                  arguments:
                    parameters:
                      - name: message
                        value: "hello"
                      - name: message
                        value: "world"

.. rule:: DAG103 Duplicate input artifacts

   The task includes several input artifacts (``<task>.arguments.artifacts``) that share the same name.
   The artifact was set multiple times.

   .. code-block:: yaml
      :emphasize-lines: 15,18

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        name: test-
      spec:
        entrypoint: main
        templates:
          - name: main
            dag:
              tasks:
                - name: process-data
                  template: data-processor
                  arguments:
                    artifacts:
                      - name: input-data
                        raw:
                          data: "data-1"
                      - name: input-data
                        raw:
                          data: "data-2"

.. DAG2xx template reference issues

.. rule:: DAG201 Self-referencing task

   The task references the current template in the ``template`` field. This may cause an infinite loop.

   Since this can still be intentional, this rule defaults to warning level.

   .. code-block:: yaml
      :emphasize-lines: 12

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        generateName: dag-
      spec:
        entrypoint: main
        templates:
          - name: main
            dag:
              tasks:
                - name: process
                  template: main

.. rule:: DAG202 Reference to a non-existent template

   The task references a template that does not exist in the workflow.

   .. code-block:: yaml
      :emphasize-lines: 12

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        generateName: dag-
      spec:
        entrypoint: main
        templates:
          - name: main
            dag:
              tasks:
                - name: process
                  template: not-exist-template

.. DAG3xx argument reference issues

.. rule:: DAG301 Invalid parameter reference

   A task input parameter contains a reference that cannot be resolved.
   This rule builds on :rule:`VAR002` but narrows the report to the task argument where the typo or mismatch occurs.

.. rule:: DAG302 Invalid artifact reference

   A task input artifact points to an artifact that is not available in the current context.
   This can happen with bare references (``inputs.artifacts.foo``) or templated expressions (``{{ inputs.artifacts.foo }}``) when the name is misspelled or simply not defined.

   .. code-block:: yaml
      :emphasize-lines: 16

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        generateName: dag-
      spec:
        entrypoint: main
        templates:
          - name: main
            dag:
              tasks:
                - name: process
                  template: compute
                  arguments:
                    artifacts:
                      - name: data
                        from: "{{ inputs.artifacts.not-exist }}"

.. rule:: DAG303 Invalid raw artifact reference

   A task input artifact uses the :py:attr:`~tugboat.schemas.Artifact.raw` block to embed a template expression, but the expression does not resolve to a known parameter.

   Raw artifacts only support parameter references (e.g. ``{{ inputs.parameters.foo }}``); pointing at artifacts leaves the expression unresolved.

   .. code-block:: yaml
      :emphasize-lines: 17

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        generateName: dag-
      spec:
        entrypoint: main
        templates:
          - name: main
            dag:
              tasks:
                - name: process
                  template: compute
                  arguments:
                    artifacts:
                      - name: data
                        raw:
                          data: "{{ inputs.artifacts.any }}"

.. rule:: DAG304 Unexpected argument parameters

   The task provides parameters that the referenced template does not declare.
   Remove the extra entries or update the target template so both sides align.

   .. code-block:: yaml
      :emphasize-lines: 17

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        generateName: dag-
      spec:
        entrypoint: main
        templates:
          - name: main
            dag:
              tasks:
                - name: process
                  template: print-message
                  arguments:
                    parameters:
                      - name: message
                        value: hello
                      - name: extra-param
                        value: ignored

          - name: print-message
            inputs:
              parameters:
                - name: message
                - name: role
                  default: user

.. DAG9xx deprecated items

.. rule:: DAG901 Deprecated Field: ``onExit``

   The ``onExit`` field in a task definition is deprecated.

   As of Argo Workflows 3.1, ``onExit`` is deprecated by the :py:class:`~tugboat.schemas.DagTask.hooks` field.
   This rule is a variant of :rule:`STP901` specific to DAG templates.

   .. code-block:: yaml
      :caption: ❌ Example manifest that violates this rule
      :emphasize-lines: 18

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        generateName: dag-
      spec:
        entrypoint: main
        templates:
          - name: main
            dag:
              tasks:
                - name: build
                  onExit: exit
                  template: run-build

          - name: run-build
            container:
              image: alpine

   .. code-block:: yaml
      :caption: ✅ Example manifest that complies with this rule
      :emphasize-lines: 13-15

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        generateName: dag-
      spec:
        entrypoint: main
        templates:
          - name: main
            dag:
              tasks:
                - name: build
                  template: run-build
            hooks:
              exit:
                template: cleanup
