Workflow Template Rules (``WT``)
================================

Code ``WT`` is used for errors specifically related to the `Workflow Template`_.
These errors are likely to cause runtime issues when the workflow template is used in a workflow.

.. _Workflow Template: https://argo-workflows.readthedocs.io/en/latest/workflow-templates/


:bdg:`WT001` Invalid entrypoint
-------------------------------

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




:bdg:`WT004` Use strict name
----------------------------

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
