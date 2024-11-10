TPL - Template Rules
====================

Code ``TPL`` is used for errors specifically related to the `template`_, the reusable and composable unit of execution in a workflow or workflow template.

.. _template: https://argo-workflows.readthedocs.io/en/latest/fields/#template


``TPL001`` - Duplicated template name
-------------------------------------

The workflow template contains multiple templates with the same name.

In the following example, the template ``hello`` is duplicated:

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: hello-
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
