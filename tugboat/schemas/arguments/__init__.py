from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from tugboat.schemas.arguments.artifact import Artifact
from tugboat.schemas.arguments.parameter import Parameter
from tugboat.schemas.basic import Array


class Arguments(BaseModel):

    model_config = ConfigDict(extra="forbid", frozen=True)

    parameters: Array[Parameter] | None = None
    artifacts: Array[Artifact] | None = None
