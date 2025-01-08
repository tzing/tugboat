from __future__ import annotations

__all__ = ["get_output_builder", "OutputBuilder"]

import tugboat.settings
from tugboat.console.outputs.base import OutputBuilder


def get_output_builder() -> OutputBuilder:
    match output_format := tugboat.settings.settings.output_format:
        case "console":
            from tugboat.console.outputs.console import ConsoleOutputBuilder

            return ConsoleOutputBuilder()

    raise RuntimeError(f"Unsupported output format: {output_format}")
