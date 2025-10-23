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
