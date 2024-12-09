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

For testing, you can use this minimal example which has a few issues:

.. code-block:: yaml
   :caption: whalesay.yaml
   :linenos:

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: test-
   spec:
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
             - "{{ inputs.parameters.messages }}" # typo: parameter's'

Save this as ``whalesay.yaml``.


Run Tugboat
+++++++++++

Lint your workflow manifest by running:

.. code-block:: bash

   tugboat whalesay.yaml

This will output a list of issues found in the manifest:

.. code-block:: none

   whalesay.yaml:5:1: M004 Missing required field 'entrypoint'

    3 | metadata:
    4 |   generateName: test-
    5 | spec:
      | └ M004 at .spec.entrypoint in test-
    6 |   templates:
    7 |     - name: whalesay

      Field 'entrypoint' is required in the 'spec' section but missing

   whalesay.yaml:16:13: VAR002 Invalid reference

    14 |         command: [cowsay]
    15 |         args:
    16 |           - "{{ inputs.parameters.messages }}" # typo: parameter's'
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
   :maxdepth: 1
   :caption: Advanced Usage

   advanced/junit

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Rules

   rules/cron-workflow
   rules/fatal-errors
   rules/manifest-errors
   rules/template
   rules/workflow
   rules/workflow-template
   rules/workflow-variable
