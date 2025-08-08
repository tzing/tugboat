from __future__ import annotations

import logging
import typing

import cloup

from tugboat.version import __version__

if typing.TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

logger = logging.getLogger(__name__)


@cloup.command(
    context_settings={
        "help_option_names": ["-h", "--help"],
    }
)
@cloup.argument(
    "manifest",
    nargs=-1,
    help="List of files or directories to check. [default: .]",
)
@cloup.option_group(
    "Input options",
    cloup.option(
        "--exclude",
        multiple=True,
        help=(
            "List of files or directories to exclude from the check. "
            "This option can be used multiple times."
        ),
    ),
    cloup.option(
        "--follow-symlinks",
        is_flag=True,
        help="Follow symbolic links when checking directories.",
    ),
)
@cloup.option_group(
    "Output options",
    cloup.option(
        "--color",
        type=cloup.BOOL,
        help="Colorize the output. [default: auto]",
    ),
    cloup.option(
        "--output-format",
        type=cloup.Choice(["console", "junit"]),
        help="Output serialization format. [default: console]",
    ),
    cloup.option(
        "-o",
        "--output-file",
        type=cloup.file_path(writable=True),
        help="File to write the diagnostic output to.",
    ),
)
@cloup.option_group(
    "Logging options",
    cloup.option(
        "-v",
        "--verbose",
        count=True,
        help="Print more information.",
    ),
)
@cloup.option(
    "--anchor",
    is_flag=True,
    help="Drop an anchor.",
)
@cloup.version_option(__version__)
def main(
    manifest: Sequence[str],
    exclude: Sequence[str],
    follow_symlinks: bool,
    color: bool | None,
    output_format: str | None,
    output_file: Path | None,
    verbose: int,
    anchor: bool,
):
    """
    Linter to streamline your Argo Workflows with precision and confidence.

    This command performs static analysis on Argo Workflow manifests to catch
    common issues and improve the quality of your workflows.

    Examples:

    \b
      # Check all YAML files in the current directory
      tugboat

    \b
      # Check specific files
      tugboat my-workflow-1.yaml my-workflow-2.yaml

    \b
      # Analyze all YAML files in a directory
      tugboat my-workflows/

    \b
      # Read from stdin
      cat my-workflow.yaml | tugboat
    """
