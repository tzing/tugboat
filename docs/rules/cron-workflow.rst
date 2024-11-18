Cron Workflow Rules (``CW``)
============================

The prefix ``CW`` is used to identify potential issues with `cron workflows`_.

.. _cron workflows: https://argo-workflows.readthedocs.io/en/latest/cron-workflows/


``CW001`` - Resource name length error
-------------------------------------

The resource name does not meet the required length criteria; it is either too long or too short.

This error is similar to :ref:`code.m009`.

Cron workflow names have a maximum length of 52 characters because Argo Workflows appends an 11-character suffix when creating the Workflow.

If the CronWorkflow name is too long, the Workflow will not be created, and no error message will be shown.
To prevent this issue, Tugboat enforces a maximum length of 52 characters for CronWorkflow names.

.. seealso::

   This specific limit is documented in the `Argo Workflows source code <https://github.com/argoproj/argo-workflows/blob/v3.5.6/workflow/validate/validate.go#L90-L93>`_.
