Step Rules (``STP``)
====================

Code ``STP`` is used for errors related to the `steps`_ in a `template`_.

.. _steps: https://argo-workflows.readthedocs.io/en/latest/walk-through/steps/
.. _template: https://argo-workflows.readthedocs.io/en/latest/fields/#template


.. STP1xx duplicated items

.. rule:: STP101 Duplicate step names

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

.. rule:: STP102 Duplicate input parameters

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

.. rule:: STP103 Duplicate input artifacts

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


.. STP2xx template reference issues

.. rule:: STP201 Self-referencing step

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

.. rule:: STP202 Reference to a non-existent template

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


.. STP3xx variable reference issues

.. rule:: STP301 Invalid parameter reference

   Found invalid parameter reference in the step input parameter.

   This rule is a variation of :rule:`VAR002`.
   It is triggered when a step input parameter references an invalid objective.

.. rule:: STP302 Invalid artifact reference

   Found invalid artifact reference in the step input artifact.

   This rule is a variation of :rule:`VAR002`.
   It is triggered when a step input artifact references an invalid objective.

   .. code-block:: yaml
      :emphasize-lines: 14

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        name: demo
      spec:
        templates:
          - name: main
            steps:
              - - name: hello
                  template: another-template
                  arguments:
                    artifacts:
                      - name: data
                        from: inputs.artifacts.invalid

.. rule:: STP303 Improper use of raw artifact field

   This rule is triggered when a raw artifact in the input arguments references something other than a parameter.
   Raw artifacts are designed to accept only parameter references, but users often mistakenly try to reference artifacts in this field.

   The purpose of this rule is to identify such cases where artifacts are incorrectly referenced.
   However, it is important to note that this rule is not limited to detecting artifact references - it also flags other types of invalid references that do not conform to the expected parameter format.

   For example, the following code demonstrates a scenario where this rule would be triggered:

   .. code-block:: yaml
      :emphasize-lines: 16

      apiVersion: argoproj.io/v1alpha1
      kind: WorkflowTemplate
      metadata:
        name: demo
      spec:
        templates:
          - name: main
            steps:
              - - name: hello
                  template: another-template
                  arguments:
                    artifacts:
                      - name: data
                        raw:
                          data: |-
                            {{ inputs.artifacts.any }}


.. STP4xx definition issues

.. rule:: STP401 Invalid step definition

   The step definition is invalid.

   This rule is triggered when the step definition does not conform to the expected structure.
   For example, it may occur if a step is nested within another step, which will result in error.

   .. code-block:: yaml
      :emphasize-lines: 12

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
                  inline:
                    steps:
                      - - name: nested-step
                          template: print-message


.. STP9xx deprecated items

.. rule:: STP901 Deprecated Field: ``onExit``

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
