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
