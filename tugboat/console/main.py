from __future__ import annotations

import collections
import contextlib
import functools
import logging
import sys
import typing

import click
import cloup
import colorlog
from pydantic import ValidationError

from tugboat.console.glob import gather_paths
from tugboat.console.outputs import get_output_builder
from tugboat.console.utils import CachedStdin
from tugboat.engine import analyze_yaml_stream
from tugboat.settings import Settings, settings
from tugboat.utils import join_with_and
from tugboat.version import __version__

if typing.TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from pydantic import FilePath


logger = logging.getLogger(__name__)


@cloup.command(
    context_settings={
        "help_option_names": ["-h", "--help"],
    }
)
@cloup.argument(
    "manifest",
    nargs=-1,
    help="List of files or directories to check. Use '-' for stdin. [default: .]",
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
    # update and validate settings
    update_settings(
        color=color,
        exclude=exclude,
        follow_symlinks=follow_symlinks,
        include=manifest,
        output_format=output_format,
    )

    logger.debug("Current settings: %s", settings.model_dump_json(indent=2))

    # determine the inputs
    manifest_paths = gather_paths(
        includes=settings.include,
        excludes=settings.exclude,
        follow_symlinks=settings.follow_symlinks,
    )

    if not manifest_paths:
        raise click.UsageError("No manifest found.")

    manifest_paths = sorted(manifest_paths)
    logger.info("Found %d manifest(s) to analyze.", len(manifest_paths))

    # analyze manifests
    counter = DiagnosesCounter()
    output_builder = get_output_builder()

    for i, path in enumerate(manifest_paths, 1):
        logger.info("[%d/%d] Analyzing file %s", i, len(manifest_paths), path)
        try:
            content = path.read_text()
        except Exception:
            logger.error("Failed to read file %s", path)
            logger.debug("Error details:", exc_info=True)
            raise click.Abort from None

        diagnoses = analyze_yaml_stream(content, path)

        counter.update(diag["type"] for diag in diagnoses)
        output_builder.update(path=path, content=content, diagnoses=diagnoses)

    logger.debug("Analysis completed. Found %d diagnoses.", sum(counter.values()))

    # write report
    if output_file:
        output_stream = output_file.open("w")
    else:
        output_stream = contextlib.nullcontext(sys.stdout)  # prevent __exit__ call

    with output_stream as stream:
        output_builder.dump(stream)

    # finalize
    click.echo(counter.summary(), err=True)

    if counter.has_any_error():
        sys.exit(2)
