from __future__ import annotations

__all__ = ["OutputFormatter", "get_output_formatter"]

import tugboat.settings
from tugboat.console.formatters.base import OutputFormatter


def get_output_formatter() -> OutputFormatter:
    match fmt := tugboat.settings.settings.output_format:
        # fmt: off
        case "console":
            from tugboat.console.formatters.console import ConsoleFormatter
            return ConsoleFormatter()

    raise RuntimeError(f"Unsupported output format: {fmt}")
