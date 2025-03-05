from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from tugboat.schemas.manifest import Manifest


class Spec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DebugManifest(Manifest[Spec]):
    """
    Internal class for debugging purposes.

    This class could be constructed with the following manifest:

    .. code-block:: yaml

        apiVersion: tugboat.example.com/v1
        kind: Debug
        metadata:
          generateName: test-
        spec:
          # add any fields here

    :meta private:
    """

    apiVersion: Literal["tugboat.example.com/v1"]  # type: ignore[reportIncompatibleVariableOverride]
    kind: Literal["Debug"]  # type: ignore[reportIncompatibleVariableOverride]
