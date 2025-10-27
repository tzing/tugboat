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
