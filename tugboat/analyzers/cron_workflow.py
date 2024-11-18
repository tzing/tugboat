from __future__ import annotations

from tugboat.core import hookimpl
from tugboat.schemas import CronWorkflow


@hookimpl
def parse_manifest(manifest: dict) -> CronWorkflow | None:
    if manifest.get("kind") == "CronWorkflow":
        return CronWorkflow.model_validate(manifest)
