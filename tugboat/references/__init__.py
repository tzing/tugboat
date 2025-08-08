"""
Reference management utilities for workflows and templates.

This module helps you track and validate variable references that are available in different workflow scopes. The core component is the :py:class:`Context` class, which maintains collections of available references for a specific scope.

For detailed information about references, see `Workflow Variables`_ in the Argo Workflows documentation.

.. _Workflow Variables: https://argo-workflows.readthedocs.io/en/latest/variables/
"""

__all__ = [
    "Context",
    "get_global_context",
    "get_step_context",
    "get_task_context",
    "get_template_context",
    "get_workflow_context",
]

from tugboat.references.context import Context
from tugboat.references.step import get_step_context, get_task_context
from tugboat.references.template import get_template_context
from tugboat.references.workflow import get_global_context, get_workflow_context
