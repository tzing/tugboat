Workflow Variable Rules (``VAR``)
=================================

The code ``VAR`` identifies potential issues with `workflow variables`_, including syntax errors, misused functions, and other related problems.

.. _workflow variables: https://argo-workflows.readthedocs.io/en/latest/variables/

.. admonition:: Known Limitations
   :class: caution

   Currently, Tugboat supports only `simple tags`_, and does not support `expression tags`_.

   This means:

   * ``{{ inputs.parameters.simple }}`` can be checked

   * ``{{= inputs.parameters.expression }}`` will be ignored

   We are planning to add support for expression tags in an upcoming release.

   .. _simple tags: https://argo-workflows.readthedocs.io/en/latest/variables/#simple
   .. _expression tags: https://argo-workflows.readthedocs.io/en/latest/variables/#expression


.. VAR1xx syntax errors

.. rule:: VAR101 Syntax error

   This error occurs when a workflow variable fails to parse due to a syntax error.

   Note that most parsers report syntax errors as soon as they encounter the first issue.
   This means the error message might not always indicate the exact location of the problem, but it provides a useful starting point for debugging.

.. rule:: VAR102 Incorrect template tag format

   This error occurs when a reference uses expression tag syntax inside a simple template tag.

   Argo Workflows supports two types of template tags:

   - **Simple tags**: ``{{ inputs.parameters.foo }}``
   - **Expression tags**: ``{{= inputs.parameters.foo }}``

   The syntax for referencing values differs between these two formats.
   Simple tags use dot notation only (e.g., ``inputs.parameters.foo``), while expression tags use `expr-lang`_ syntax, which supports both dot notation and bracket notation for member access (e.g., ``inputs.parameters['foo']`` or ``inputs["parameters"]["foo"]``).

   This error is reported when expression tag syntax is mistakenly used inside a simple tag.

   .. code-block:: yaml
      :emphasize-lines: 14

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        generateName: test-
      spec:
        entrypoint: whalesay
        templates:
          - name: whalesay
            inputs:
              parameters:
                - name: message
            container:
              image: docker/whalesay:latest
              args: ["{{ inputs.parameters['message'] }}"]

   In the example above, ``inputs.parameters['message']`` uses bracket notation, which is valid in expression tags but not in simple tags.
   The correct format for a simple tag is ``{{ inputs.parameters.message }}``.

   .. _expr-lang: https://expr-lang.org/


.. VAR2xx invalid references

.. rule:: VAR201 Unknown Argo workflow variable reference

   This error occurs when a reference is not recognized as a valid Argo workflow variable in the current context.

   Tugboat validates references against a list of known Argo workflow variables based on the template type and defined inputs/outputs.
   If a reference cannot be matched to any known variable, this error is reported.

   .. code-block:: yaml
      :emphasize-lines: 18

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        generateName: test-
      spec:
        entrypoint: main
        templates:
          - name: main
            inputs:
              parameters:
                - name: message
            steps:
              - - name: step-1
                  template: produce
                  arguments:
                    parameters:
                      - name: msg
                        value: "{{ inputs.parameters.msg }}"
              - - name: step-2
                  template: consume
                  arguments:
                    parameters:
                      - name: msg
                        value: "{{ steps.step-1.outputs.parameters.massage }}"

   In the example above, ``inputs.parameters.msg`` is reported because the defined parameter is named ``message``, not ``msg``.

   When possible, Tugboat will suggest the closest matching variable name as a fix.

   .. note::

      Tugboat can only validate references within the same manifest.
      References to step outputs (e.g., ``steps.step-1.outputs.parameters.message``) cannot be fully validated because the output is defined by the referenced template, which may be a WorkflowTemplate defined elsewhere.

.. rule:: VAR202 Not an Argo workflow variable reference

   This warning occurs when a template tag contains a single identifier that does not match any known Argo workflow variable pattern.

   Argo workflow variables typically have a dotted format like ``inputs.parameters.name`` or ``workflow.name``.
   When a tag contains only a simple variable name (e.g., ``{{ foo }}``), it is unlikely to be an Argo variable.

   .. code-block:: yaml
      :emphasize-lines: 14

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        generateName: test-
      spec:
        entrypoint: whalesay
        templates:
          - name: whalesay
            container:
              image: docker/whalesay:latest
              args: ["{{ message }}"]

   In the example above, ``{{ message }}`` is flagged because ``message`` is not a valid Argo workflow variable.

   This warning is commonly triggered when:

   - The manifest uses another templating engine (e.g., Jinja2, Helm) that shares the ``{{ }}`` syntax
   - There is a typo or incomplete variable reference

   If the tag is intended for another templating engine, you can suppress this warning by adding a ``# noqa: VAR202`` comment. See :doc:`../violations` for more information on suppressing warnings.
