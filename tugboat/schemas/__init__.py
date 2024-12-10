"""
:py:mod:`tugboat.schemas` contains classes representing the schemas of Argo Workflows.

All the listed classes are :py:class:`pydantic.BaseModel` classes used for input
data validation. These classes are immutable and do not allow any extra fields.
This ensures that the input data strictly follows the schema and that the data
model remains consistent throughout the program's execution, even when data is
transferred between different modules.

All the classes are derived from Argo Workflows' official `Field Reference`_
documentation. If you find any discrepancies between the classes and the official
documentation, please report it as a bug.

Currently, many of the members are typed as :py:data:`typing.Any`.
This means that the field is not yet used in the codebase but is included in the
schema for future compatibility. This also provides the basic ability to validate
if there are any incompatible fields in the input data.

.. _Field Reference: https://argo-workflows.readthedocs.io/en/latest/fields/
"""

__all__ = [
    "Arguments",
    "Artifact",
    "ContainerTemplate",
    "CronWorkflow",
    "Manifest",
    "Parameter",
    "ScriptTemplate",
    "Step",
    "Template",
    "Workflow",
    "WorkflowTemplate",
]

from tugboat.schemas.arguments import Arguments, Artifact, Parameter
from tugboat.schemas.cron_workflow import CronWorkflow
from tugboat.schemas.manifest import Manifest
from tugboat.schemas.template import ContainerTemplate, ScriptTemplate, Step, Template
from tugboat.schemas.workflow import Workflow, WorkflowTemplate
