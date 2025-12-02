Workflow Variable Rules (``VAR``)
=================================

The code ``VAR`` identifies potential issues with `workflow variables`_, including syntax errors, misused functions, and other related problems.

.. _workflow variables: https://argo-workflows.readthedocs.io/en/latest/variables/

Known limitations
-----------------

Currently, Tugboat supports only `simple template tags`_, and does not support `expression template tags`_.

This means:

.. code-block:: none

   {{ inputs.parameters.foo }} can be checked

   but {{= inputs.parameters.foo }} will be ignored

We are planning to add support for expression template tags in an upcoming release.

.. _simple template tags: https://argo-workflows.readthedocs.io/en/latest/variables/#simple
.. _expression template tags: https://argo-workflows.readthedocs.io/en/latest/variables/#expression


Rules
-----

.. rule:: VAR001 Syntax error

   This error occurs when a workflow variable fails to parse due to a syntax error.

   Note that most parsers report syntax errors as soon as they encounter the first issue.
   This means the error message might not always indicate the exact location of the problem, but it provides a useful starting point for debugging.

.. rule:: VAR002 Misused reference

   A reference used in the manifest is not defined in the current context.

   Tugboat checks the references used in the manifest against a list of references from the `official documentation <https://argo-workflows.readthedocs.io/en/latest/variables/#reference>`_.
   If a reference used in the manifest is not found in the defined references, an error is reported.

   .. code-block:: yaml
      :emphasize-lines: 17

      apiVersion: argoproj.io/v1alpha1
      kind: Workflow
      metadata:
        generateName: test-
      spec:
        entrypoint: whalesay
        templates:
          - name: whalesay
            inputs:
              artifacts:
                - name: message
                  raw:
                    data: Hello Tugboat!
            container:
              image: docker/whalesay:latest
              command: [cowsay]
              args: ["{{ inputs.artifacts.message }}"]

   In the example above, ``inputs.artifacts.message`` is invalid because referencing artifacts in this field is not allowed.

   .. admonition:: Limited validation of step outputs
      :class: note

      Tugboat can only validate references within the same manifest.

      The outputs of a step are defined by the template it refers to.
      Tugboat cannot validate these outputs because their definitions are not included in the same manifest.
      This means Tugboat cannot verify references that point to the outputs of other steps.

.. VAR1xx syntax errors

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
