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


:bdg:`STP002` Duplicated input parameter name
---------------------------------------------

The step contains multiple input parameters with the same name.

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     name: test-
   spec:
     entrypoint: main
     templates:
       - name: main
         steps:
           - - name: hello
               template: print-message
               arguments:
                 parameters:
                   - name: message
                     #     ^^^^^^^ This parameter is duplicated
                     value: hello-1
                   - name: message
                     #     ^^^^^^^ This parameter is duplicated
                     value: hello-2

:bdg:`TPL003` Duplicated input artifact name
--------------------------------------------

The step contains multiple input artifacts with the same name.

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     name: test-
   spec:
     entrypoint: main
     templates:
       - name: main
         steps:
           - - name: hello
               template: print-message
               arguments:
                 artifacts:
                   - name: message
                     #     ^^^^^^^ This argument is duplicated
                     raw:
                       data: hello-1
                   - name: message
                     #     ^^^^^^^ This argument is duplicated
                     raw:
                       data: hello-2
