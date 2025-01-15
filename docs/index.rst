Tugboat
=======

Welcome to Tugboat, your dedicated companion for validating and improving Argo Workflow manifests.

As a linter for `Argo Workflows`_, Tugboat helps you identify and resolve potential issues before they become runtime problems, saving you time and ensuring smoother deployments.

.. _Argo Workflows: https://argoproj.github.io/workflows/

.. figure:: /_static/images/screenshot.png
   :alt: Screenshot of tugboat command
   :align: center

Argo Workflows empower developers to orchestrate complex containerized processes, but designing error-free manifests can be challenging.

Tugboat provides a range of features tailored to the needs of Argo Workflow users:

- ⚙️ Syntax Validation
   - Catch common mistakes that might cause workflows to fail at runtime.

- 🔍 Error Detection
   - Highlight undefined, unused, or misconfigured references within manifests.

- 📘 Argo Workflow Support
   - Designed to align with Argo Workflow specifications, Tugboat ensures compatibility with supported versions of Argo.

- 🚀 Lightweight and Fast
   - Tugboat integrates seamlessly into your development workflow, offering quick feedback without compromising your pace.

- 📊 Actionable Insights
   - Clear, actionable error messages and warnings to help you fix issues efficiently.

.. note::

   Tugboat in currently in development and may not yet cover every use case or workflow configuration.

   While Tugboat provides valuable linting capabilities, certain rules may be overly strict or aggressive in their assessments.
   We are eager to hear from users like you — your feedback will directly influence how we refine and improve Tugboat.


Quick Start
-----------

To get started with Tugboat, you can install it using pip:

Install Tugboat
+++++++++++++++

Tugboat requires Python 3.12 or later (download from the `Python website <https://www.python.org/downloads/>`_ if needed).

The package is available on PyPI as `argo-tugboat`_. Install it using pip:

.. code-block:: bash

   pip install argo-tugboat

.. _argo-tugboat: https://pypi.org/project/argo-tugboat/


Prepare workflow manifest
+++++++++++++++++++++++++

Make sure you have an Argo Workflow manifest ready. It should be a valid YAML file.

For testing, you can use this minimal example:

.. code-block:: yaml
   :caption: whalesay.yaml
   :linenos:
   :emphasize-lines: 6,17

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: test-
   spec:
     entrypoint: ducksay
     templates:
       - name: whalesay
         inputs:
           parameters:
             - name: message
               value: Hello Argo!
         container:
           image: docker/whalesay:latest
           command: [cowsay]
           args:
             - "{{ inputs.parameters.messages }}"

This manifest has two issues:

- The entrypoint ``ducksay`` is not defined in any template.
- The parameter reference is typo; it should be ``message`` instead of ``messages``.

Save this as ``whalesay.yaml``.


Run Tugboat
+++++++++++

Lint your workflow manifest by running:

.. code-block:: bash

   tugboat whalesay.yaml

This will output a list of issues found in the manifest:

.. code-block:: none

   whalesay.yaml:6:3: WF001 Invalid entrypoint

    4 |   generateName: test-
    5 | spec:
    6 |   entrypoint: ducksay
      |               ^^^^^^^
      |               └ WF001 at .spec.entrypoint in test-
    7 |   templates:
    8 |     - name: whalesay

      Entrypoint 'ducksay' is not defined in any template.
      Defined entrypoints: 'whalesay'.

      Do you mean: whalesay

   whalesay.yaml:17:13: VAR002 Invalid reference

    15 |         command: [cowsay]
    16 |         args:
    17 |           - "{{ inputs.parameters.messages }}"
       |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
       |              └ VAR002 at .spec.templates.0.container.args.0 in test-

       The parameter reference 'inputs.parameters.messages' used in template 'whalesay' is invalid.

       Do you mean: {{ inputs.parameters.message }}

   Found 2 failures

For more information on how to use Tugboat, runs its help command:

.. code-block:: bash

   tugboat --help


.. toctree::
   :hidden:

   user/violations
   user/configuration
   user/junit

.. toctree::
   :hidden:
   :caption: Rules

   rules/cron-workflow
   rules/fatal-errors
   rules/manifest-errors
   rules/step
   rules/template
   rules/workflow
   rules/workflow-template
   rules/workflow-variable

.. toctree::
   :hidden:
   :caption: Development

   api/index
