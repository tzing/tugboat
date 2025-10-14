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


Get Tugboat
+++++++++++

Tugboat requires `Python`_ 3.12 or later.

The package is available on PyPI as `argo-tugboat`_. Just pick your favorite way to install it:

.. tab-set::

    .. tab-item:: pipx :iconify:`simple-icons:pipx`

       .. code-block:: bash

          # install
          pipx install argo-tugboat

          # invoke without installing
          pipx run argo-tugboat

    .. tab-item:: uv :iconify:`simple-icons:uv`

       .. code-block:: bash

          # invoke without installing
          uvx --from=argo-tugboat tugboat

    .. tab-item:: pip :iconify:`file-icons:pypi`

       .. code-block:: bash

          pip install argo-tugboat

.. _Python: https://www.python.org/downloads/
.. _argo-tugboat: https://pypi.org/project/argo-tugboat/


Argo Workflows Manifest
+++++++++++++++++++++++

To get started, find an Argo Workflow manifest that contains an error.
For example, the following manifest has an invalid entrypoint:

.. code-block:: yaml
   :caption: whalesay.yaml
   :linenos:
   :emphasize-lines: 6

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
             - "{{ inputs.parameters.message }}"


Run :octicon:`rocket`
+++++++++++++++++++++

Lint your workflow manifest by running:

.. code-block:: bash

   tugboat whalesay.yaml

This will output the following:

.. code-block:: none

   WF201 Invalid entrypoint
     @whalesay.yaml:6:15 (test-)

     4 |   generateName: test-
     5 | spec:
     6 |   entrypoint: ducksay
       |               ^^^^^^^
       |               └ WF201 at .spec.entrypoint
     7 |   templates:
     8 |     - name: whalesay

     Entrypoint 'ducksay' is not defined in any template.
     Defined entrypoints: 'whalesay'

     Do you mean: whalesay

   Found 1 failures

For more information on how to use Tugboat, runs its help command:

.. code-block:: bash

   tugboat --help


.. toctree::
   :hidden:

   user/configuration
   user/violations
   user/mcp

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
   changelog
