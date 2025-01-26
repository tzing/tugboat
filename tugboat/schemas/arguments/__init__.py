from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from tugboat.schemas.arguments.artifact import Artifact
from tugboat.schemas.arguments.parameter import Parameter
from tugboat.schemas.basic import Array


class Arguments(BaseModel):
    """
    `Arguments` to a template.

    .. _Arguments: https://argo-workflows.readthedocs.io/en/latest/fields/#arguments
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    artifacts: Array[Artifact] | None = None
    """Artifacts is the list of artifacts to pass to the template or workflow."""
    parameters: Array[Parameter] | None = None
    """Parameters is the list of parameters to pass to the template or workflow."""
