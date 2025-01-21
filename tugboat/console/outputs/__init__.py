from __future__ import annotations

__all__ = [
    "OutputBuilder",
    "get_output_builder",
]

import tugboat.settings
from tugboat.console.outputs.base import OutputBuilder


def get_output_builder() -> OutputBuilder:
    match output_format := tugboat.settings.settings.output_format:
        case "console":
            from tugboat.console.outputs.console import ConsoleOutputBuilder

            return ConsoleOutputBuilder()

        case "junit":
            from tugboat.console.outputs.junit import JUnitOutputBuilder

            return JUnitOutputBuilder()

    raise RuntimeError(f"Unsupported output format: {output_format}")
