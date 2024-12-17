Step Rules (``STP``)
====================

Code ``STP`` is used for errors related to the `steps`_ in a `template`_.

.. _steps: https://argo-workflows.readthedocs.io/en/latest/walk-through/steps/
.. _template: https://argo-workflows.readthedocs.io/en/latest/fields/#template


:bdg:`STP001` Duplicated step name
----------------------------------

The template contains multiple steps with the same name.

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: steps-
   spec:
     entrypoint: hello-hello
     templates:
       - name: hello-hello
         steps:
           - - name: hello
               #     ^^^^^ This step is duplicated
               template: print-message
               arguments:
                 parameters:
                   - name: message
                     value: "hello-1"
           - - name: hello
               #     ^^^^^ This step is duplicated
               template: print-message
               arguments:
                 parameters:
                   - name: message
                     value: "hello-2"
