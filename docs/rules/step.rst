Step Rules (``STP``)
====================

Code ``STP`` is used for errors related to the `steps`_ in a `template`_.

.. _steps: https://argo-workflows.readthedocs.io/en/latest/walk-through/steps/
.. _template: https://argo-workflows.readthedocs.io/en/latest/fields/#template


:bdg:`STP001` Duplicate step names
----------------------------------

The template contains multiple steps with the same name.

.. code-block:: yaml
   :emphasize-lines: 10,16

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
               template: print-message
               arguments:
                 parameters:
                   - name: message
                     value: "hello-1"
           - - name: hello
               template: print-message
               arguments:
                 parameters:
                   - name: message
                     value: "hello-2"


:bdg:`STP002` Duplicate input parameters
----------------------------------------

The step includes several input parameters (``<step>.arguments.parameters``) that share the same name.
The parameter was set multiple times.

.. code-block:: yaml
   :emphasize-lines: 14,16

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
                     value: hello-1
                   - name: message
                     value: hello-2

:bdg:`STP003` Duplicate input artifacts
---------------------------------------

The step includes several input artifacts (``<step>.arguments.artifacts``) that share the same name.
The artifact was set multiple times.

.. code-block:: yaml
   :emphasize-lines: 14,17

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
                     raw:
                       data: hello-1
                   - name: message
                     raw:
                       data: hello-2

:bdg:`STP004` Deprecated Field: ``onExit``
-------------------------------------------

The ``onExit`` field in the step definition is deprecated.

As of Argo Workflow version 3.1, the ``onExit`` field is deprecated.
It is recommended to use the ``hooks[exit].template`` field instead.

.. code-block:: yaml
   :caption: ❌ Example of incorrect code for this rule
   :emphasize-lines: 11

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: exit-handler-step-level-
   spec:
     entrypoint: main
     templates:
       - name: main
         steps:
           - - name: hello1
               onExit: exit
               template: print-message
               arguments:
                 parameters: [{name: message, value: "hello1"}]

.. code-block:: yaml
   :caption: ✅ Example of correct code for this rule
   :emphasize-lines: 14-16

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: exit-handler-step-level-
   spec:
     entrypoint: main
     templates:
       - name: main
         steps:
           - - name: hello1
               template: print-message
               arguments:
                 parameters: [{ name: message, value: "hello1" }]
               hooks:
                 exit:
                   template: exit


:bdg:`STP005` Self-referencing step
-----------------------------------

The step references itself in the ``template`` field. This may cause an infinite loop.

Since this may still be a intended behavior, this rule is default to warning level.

.. code-block:: yaml
   :emphasize-lines: 11

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: test-
   spec:
     entrypoint: main
     templates:
       - name: main
         steps:
           - - name: hello
               template: main


:bdg:`STP006` Reference to a non-existent template
--------------------------------------------------

The step references a non-existent template.

.. code-block:: yaml
   :emphasize-lines: 11

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: test-
   spec:
     entrypoint: main
     templates:
       - name: main
         steps:
           - - name: hello
               template: non-existent-template

.. note::

  This rule verifies the presence of a template within the same workflow.

  If the template is defined in a different workflow and referenced using ``templateRef``, this rule will not detect it.
  Tugboat does not currently support cross-workflow checks, even if the referenced workflow is included in the same run.
