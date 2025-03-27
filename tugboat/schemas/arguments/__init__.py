from __future__ import annotations

import functools

from pydantic import BaseModel, ConfigDict

from tugboat.schemas.arguments.artifact import Artifact, RelaxedArtifact
from tugboat.schemas.arguments.parameter import Parameter, RelaxedParameter
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

    @functools.cached_property
    def parameter_dict(self) -> dict[str, Parameter]:
        """
        Parameter name to :py:attr:`parameters` mapping.
        """
        return {
            parameter.name: parameter
            for parameter in self.parameters or ()
            if parameter.name
        }

    @functools.cached_property
    def artifact_dict(self) -> dict[str, Artifact]:
        """
        Artifact name to :py:attr:`artifacts` mapping.
        """
        return {
            artifact.name: artifact
            for artifact in self.artifacts or ()
            if artifact.name
        }


class RelaxedArguments(Arguments):
    """
    A relaxed version of :py:class:`Arguments` that allows some often misused
    fields. This is useful for skipping Pydantic validation and handle it during
    later processing.
    """

    parameters: Array[RelaxedParameter] | None = None  # type: ignore[reportIncompatibleVariableOverride]
    artifacts: Array[RelaxedArtifact] | None = None  # type: ignore[reportIncompatibleVariableOverride]
