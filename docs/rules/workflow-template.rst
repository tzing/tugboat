Workflow Template Rules (``WT``)
================================

Code ``WT`` is used for errors specifically related to the `Workflow Template`_.
These errors are likely to cause runtime issues when the workflow template is used in a workflow.

.. _Workflow Template: https://argo-workflows.readthedocs.io/en/latest/workflow-templates/


``WT001`` - Invalid entrypoint
------------------------------

The specified entrypoint does not exist in the workflow template.

For instance, the following workflow specifies an entrypoint that does not exist:

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: WorkflowTemplate
   metadata:
     name: demo
   spec:
     entrypoint: non-existent
     #           ^^^^^^^^^^^^ This entrypoint does not exist
     templates:
       - name: hello
         container:
           image: alpine:latest


``WT002`` - Duplicated parameter name
-------------------------------------

The workflow template contains multiple argument parameters with the same name.

In the following example, the template ``message`` is duplicated:

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: WorkflowTemplate
   metadata:
     name: demo
   spec:
     arguments:
       parameters:
         - name: message
           #     ^^^^^^^ This parameter is duplicated
           value: "Hello, World!"
         - name: message
           #     ^^^^^^^ This parameter is duplicated
           value: "Hello, Tugboat!"


``WT003`` - Duplicated artifact name
------------------------------------

The workflow template contains multiple argument artifacts with the same name.

In the following example, the artifact ``message`` is duplicated:

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: WorkflowTemplate
   metadata:
     name: demo
   spec:
     arguments:
       artifacts:
         - name: message
           #     ^^^^^^^ This parameter is duplicated
           raw:
              data: "Hello, World!"
         - name: message
           #     ^^^^^^^ This parameter is duplicated
           raw:
              data: >-
                Hello, Tugboat!


``WT004`` - Use strict name
---------------------------

This error occurs when a workflow template uses the ``metadata.generateName`` field instead of the ``metadata.name`` field.

While Argo Workflows does not strictly enforce this, it is recommended to use the ``metadata.name`` field for workflow templates.
This is because the workflow template will be referenced by its name in the workflow, and a randomly generated name can be difficult to remember.

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: WorkflowTemplate
   metadata:
     generateName: demo-
     #^^^^^^^^^^^^^^^^^^ Use `name` instead of `generateName`
   spec:
     templates: []
