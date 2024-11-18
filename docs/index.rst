Tugboat
=======

A linter to streamline your `Argo Workflows`_ with precision and confidence.

.. _Argo Workflows: https://argoproj.github.io/workflows/

.. figure:: /_static/images/screenshot.png
   :alt: Screenshot of tugboat command
   :align: center

.. attention::

   Tugboat is currently in development. Stay tuned for updates!


Installation
------------

Tugboat is available on PyPI as `argo-tugboat`_. You can install it using pip:

.. code-block:: bash

   pip install argo-tugboat

.. _argo-tugboat: https://pypi.org/project/argo-tugboat/


Usage
-----

This tool introduces a command, ``tugboat``, which you can use to lint your Argo Workflows manifests.

.. code-block:: bash

   tugboat

This command will, by default, lint all ``.yaml`` or ``.yml`` files in the current directory.
You can also specify particular files to lint by passing them as arguments:

.. code-block:: bash

   tugboat file1.yaml file2.yaml


Example
-------

For instance, if you have a manifest file named ``whalesay.yaml`` with the following content:

.. code-block:: yaml
   :linenos:
   :caption: whalesay.yaml

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: test-
   spec:
     entrypoint: ducksay
     templates:
       - name: whalesay
         container:
           image: docker/whalesay:latest
           command: [cowsay]
           args: ["hello world"]

The command will output the following:

.. code-block:: none

   whalesay.yaml:6:3: WF001 Invalid entrypoint

    4 |   generateName: test-
    5 | spec:
    6 |   entrypoint: ducksay
      |               ^^^^^^^
      |               └ WF001 at .spec.entrypoint in test-
    7 |   templates:

      Entrypoint 'ducksay' is not defined in any template.
      Defined entrypoints: 'whalesay'.

      Do you mean: whalesay

   Found 1 failures


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
