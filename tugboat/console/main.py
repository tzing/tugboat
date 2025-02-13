from __future__ import annotations

import collections
import contextlib
import logging
import sys
import typing
from pathlib import Path

import click
import cloup
import colorlog
from pydantic import ValidationError

from tugboat.analyze import analyze_yaml
from tugboat.console.glob import gather_paths
from tugboat.console.outputs import get_output_builder
from tugboat.console.utils import VirtualPath
from tugboat.settings import settings
from tugboat.utils import join_with_and
from tugboat.version import __version__

if typing.TYPE_CHECKING:
    from collections.abc import Sequence

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
@cloup.version_option(__version__)
def main(
    manifest: Sequence[str],
    exclude: Sequence[str],
    follow_symlinks: bool,
    color: bool | None,
    output_format: str | None,
    output_file: Path | None,
    verbose: int,
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
      cat my-workflow.yaml | tugboat -
    """
    # setup logging
    setup_logging(verbose)
    logger.debug("Tugboat sets sail!")

    # update and validate settings
    if manifest == ("-",):
        # NOTE
        # This is a workaround to handle `-`, which stands for stdin.
        # We want to keep `-` as a valid command line option, but not allow it in the configuration file.
        # So, the `Settings` object will reject this value during validation.
        # This workaround deals with it separately to avoid validation errors.
        # If you have a better solution, feel free to submit a PR! :)
        include = ()
    else:
        include = manifest

    update_settings(
        color=color,
        exclude=exclude,
        follow_symlinks=follow_symlinks,
        include=include,
        output_format=output_format,
    )

    logger.debug("Current settings: %s", settings.model_dump_json(indent=2))

    # determine the inputs
    if manifest == ("-",):
        manifest_paths = [VirtualPath(sys.stdin.name, sys.stdin)]
        manifest_paths = typing.cast(list[Path], manifest_paths)
    else:
        manifest_paths = gather_paths(
            settings.include, settings.exclude, settings.follow_symlinks
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

        diagnoses = analyze_yaml(content)

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


def setup_logging(verbose_level: int):
    """
    Setup logging
    We separate the configuration of the tugboat logger from the other loggers.
    """
    # tugboar loggers
    tugboat_logger = colorlog.getLogger("tugboat")
    tugboat_logger.propagate = False

    match verbose_level:
        case 0:
            tugboat_logger.setLevel(colorlog.WARNING)
        case 1:
            tugboat_logger.setLevel(colorlog.INFO)
        case _:
            tugboat_logger.setLevel(colorlog.DEBUG)

    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter("%(log_color)s%(levelname)7s |%(reset)s %(message)s")
    )
    tugboat_logger.addHandler(handler)

    # other loggers
    # only show logs when verbose level >= 3
    if verbose_level >= 3:
        logger = colorlog.getLogger()
        logger.setLevel(colorlog.DEBUG)
        logger.addHandler(handler)


def update_settings(**kwargs):
    """Update the settings, if the option is provided by the user."""
    update_args = {}

    # general settings
    for key in (
        "exclude",
        "follow_symlinks",
        "include",
        "output_format",
    ):
        if value := kwargs.get(key):
            update_args[key] = value

    for key in ("color",):
        if (value := kwargs.get(key)) is not None:
            update_args[key] = value

    # inplace update
    # https://docs.pydantic.dev/latest/concepts/pydantic_settings/#in-place-reloading
    try:
        settings.__init__(**update_args)
    except ValidationError as e:
        for err in e.errors():
            field = ".".join(map(str, err["loc"]))
            msg = err["msg"]
            raise click.UsageError(f"{field}: {msg}") from None


class DiagnosesCounter(collections.Counter):

    def summary(self) -> str:
        parts = []
        if count := self["error"]:
            parts.append(f"{count} errors")
        if count := self["failure"]:
            parts.append(f"{count} failures")
        if count := self["skipped"]:
            parts.append(f"{count} skipped checks")

        if parts:
            summary = join_with_and(parts, quote=False)
            return f"Found {summary}"

        return "All passed!"

    def has_any_error(self) -> bool:
        return any((self["error"], self["failure"]))
