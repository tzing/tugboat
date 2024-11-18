CW - Cron Workflow Rules
========================

The prefix ``CW`` is reserved for identifying potential issues with cron workflows.

Currently, there are no specific linting rules for cron workflows.

However, Tugboat does check the schema of cron workflows and raises errors if the schema is invalid, using the :doc:`manifest-errors` rule set.

.. _cron workflows: https://argo-workflows.readthedocs.io/en/latest/cron-workflows/
