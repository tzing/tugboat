"""
Utilities for building available references within the given scope.

See Also
--------
Reference
   https://argo-workflows.readthedocs.io/en/latest/variables/#reference
"""

__all__ = [
    "Context",
    "get_global_context",
    "get_workflow_context",
]

from tugboat.references.context import Context
from tugboat.references.workflow import get_global_context, get_workflow_context
