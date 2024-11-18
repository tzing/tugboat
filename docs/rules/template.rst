Template Rules (``TPL``)
========================

Code ``TPL`` is used for errors specifically related to the `template`_, the reusable and composable unit of execution in a workflow or workflow template.

.. _template: https://argo-workflows.readthedocs.io/en/latest/fields/#template


``TPL001`` - Duplicated template name
-------------------------------------

The workflow or workflow template contains multiple templates with the same name.

In the following example, the template ``hello`` is duplicated:

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: WorkflowTemplate
   metadata:
     name: demo
   spec:
     templates:
       - name: hello
         #     ^^^^^ This template is duplicated
         container:
           image: alpine:latest
       - name: hello
         #     ^^^^^ This template is duplicated
         container:
           image: alpine:latest


``TPL002`` - Duplicated input parameter name
--------------------------------------------

The template contains multiple input parameters with the same name.

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: WorkflowTemplate
   metadata:
     name: demo
   spec:
     templates:
        - name: main
          inputs:
            parameters:
              - name: message
              - name: message
                #     ^^^^^^^ This parameter is duplicated


``TPL003`` - Duplicated input artifact name
-------------------------------------------

The template contains multiple input artifacts with the same name.

.. code-block:: yaml

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
              - name: data
                #     ^^^^ This artifact is duplicated


``TPL004`` - Duplicated output parameter name
---------------------------------------------

The template contains multiple output parameters with the same name.

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: WorkflowTemplate
   metadata:
     name: demo
   spec:
     templates:
        - name: main
          outputs:
            parameters:
              - name: message
              - name: message
                #     ^^^^^^^ This parameter is duplicated


``TPL005`` - Duplicated output artifact name
--------------------------------------------

The template contains multiple output artifacts with the same name.

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: WorkflowTemplate
   metadata:
     name: demo
   spec:
     templates:
        - name: main
          outputs:
            artifacts:
              - name: data
              - name: data
                #     ^^^^ This artifact is duplicated
