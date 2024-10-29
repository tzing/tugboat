from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from tugboat.schemas.arguments.artifact import Artifact
from tugboat.schemas.arguments.parameter import Parameter


class Arguments(BaseModel):

    model_config = ConfigDict(extra="forbid")

    parameters: list[Parameter] | None = None
    artifacts: list[Artifact] | None = None
