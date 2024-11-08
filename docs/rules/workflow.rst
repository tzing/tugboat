WF - Workflow Rules
===================

Code ``WF`` is used for issues closely related to the `Workflow`_.
These issues are likely to cause runtime errors when the workflow is executed.

.. _Workflow: https://argo-workflows.readthedocs.io/en/latest/workflow-concepts/#the-workflow


.. _code.wf001:

``WF001`` - Invalid entrypoint
------------------------------

The specified entrypoint does not exist in the workflow.

For instance, the following workflow specifies an entrypoint that does not exist:

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: hello-
   spec:
     entrypoint: non-existent
     #           ^^^^^^^^^^^^ This entrypoint does not exist
     templates:
       - name: hello
         container:
           image: alpine:latest


``WF002`` - Duplicated template name
------------------------------------

The workflow contains multiple templates with the same name.

In the following example, the template ``hello`` is duplicated:

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: hello-
   spec:
     entrypoint: hello
     templates:
       - name: hello
         #     ^^^^^ This template is duplicated
         container:
           image: alpine:latest
       - name: hello
         #     ^^^^^ This template is duplicated
         container:
           image: alpine:latest


``WF003`` - Duplicated parameter name
-------------------------------------

The workflow contains multiple argument parameters with the same name.

In the following example, the template ``message`` is duplicated:

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: hello-
   spec:
     arguments:
       parameters:
         - name: message
           #     ^^^^^^^ This parameter is duplicated
           value: "Hello, World!"
         - name: message
           #     ^^^^^^^ This parameter is duplicated
           value: "Hello, Tugboat!"


``WF004`` - Duplicated artifact name
------------------------------------

The workflow contains multiple argument artifacts with the same name.

In the following example, the artifact ``message`` is duplicated:

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: hello-
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
