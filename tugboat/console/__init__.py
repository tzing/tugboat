from __future__ import annotations

import contextlib
import logging
import sys
import typing

import click
import cloup
import colorlog
from pydantic import ValidationError

import tugboat.console.anchor
import tugboat.settings
from tugboat.console.formatters import get_output_formatter
from tugboat.console.glob import gather_paths
from tugboat.console.utils import DiagnosesCounter, Stdin
from tugboat.engine import analyze_yaml_stream
from tugboat.settings import settings
from tugboat.version import __version__

if typing.TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path
    from typing import Any, NoReturn, TextIO

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
        "--follow-symlinks/--no-follow-symlinks",
        default=None,
        help="Follow symbolic links when checking directories.",
    ),
)
@cloup.option_group(
    "Output options",
    cloup.option(
        "--color/--no-color",
        default=None,
        help="Colorize the output. [default: auto]",
    ),
    cloup.option(
        "--output-format",
        type=cloup.Choice(["console", "junit", "github"]),
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
    "--mcp",
    is_flag=True,
    help="Start the MCP server.",
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
    follow_symlinks: bool | None,
    color: bool | None,
    output_format: str | None,
    output_file: Path | None,
    verbose: int,
    mcp: bool,
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
    # setup logging
    setup_loggings(verbose)
    logger.debug("Tugboat sets sail!")

    # easter egg: drop an anchor
    if anchor:
        tugboat.console.anchor.print_anchor()

    # update and validate settings
    update_settings(**locals())
    logger.debug(
        "Current settings: %s",
        tugboat.settings.settings.model_dump_json(indent=2),
    )

    # special case: MCP
    if mcp:
        run_mcp()

    # perform linting
    if output_file:
        output_stream = output_file.open("w")
    else:
        # `nullcontext` prevents __exit__ call
        output_stream = typing.cast("TextIO", contextlib.nullcontext(sys.stdout))

    lint(output_stream)


def setup_loggings(verbose_level: int):
    """
    Setup loggings

    We separate the configuration of the tugboat logger from the other loggers.
    """
    # tugboat loggers
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


def update_settings(
    manifest: Sequence[str],
    exclude: Sequence[str],
    follow_symlinks: bool | None,
    color: bool | None,
    output_format: str | None,
    **sink,
):
    """
    Update settings using command line arguments.

    This function replaces any settings loaded from config files or environment
    variables with values provided through command line options.

    The updates are applied directly to the settings object.
    """
    # pass the input options to the settings data model for validation
    update_args: dict[str, Any] = {
        "include": manifest,
        "exclude": exclude,
    }

    if color is not None:
        update_args["color"] = color
    if follow_symlinks is not None:
        update_args["follow_symlinks"] = follow_symlinks
    if output_format is not None:
        update_args["output_format"] = output_format

    # update settings
    with reraise_usage_error():
        # https://docs.pydantic.dev/latest/concepts/pydantic_settings/#in-place-reloading
        tugboat.settings.settings.__init__(**update_args)

    # special case: stdin
    if manifest == () and not sys.stdin.isatty() and not sys.stdin.closed:
        logger.debug("Detected stdin. Using it as input.")
        path = typing.cast("FilePath", Stdin())
        tugboat.settings.settings.include = [path]


@contextlib.contextmanager
def reraise_usage_error():
    try:
        yield
    except ValidationError as e:
        # only use the first error
        err, *_ = e.errors()

        match setting_name := err["loc"][0]:
            case "include":
                option_name = "manifest"
            case "exclude":
                option_name = "--exclude"
            case "color":
                option_name = "--color"
            case "follow_symlinks":
                option_name = "--follow-symlinks"
            case "output_format":
                option_name = "--output-format"
            case _:
                option_name = setting_name  # pragma: no cover

        value = err["input"]
        message = err["msg"]
        raise click.UsageError(
            f"Invalid value for '{option_name}': {message} (input= {value})"
        ) from None


def lint(output_stream: TextIO) -> NoReturn:
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
    output_formatter = get_output_formatter()

    for i, path in enumerate(manifest_paths, 1):
        logger.info("[%d/%d] Analyzing file %s", i, len(manifest_paths), path)
        try:
            content = path.read_text()
        except Exception:
            logger.error("Failed to read file %s", path)
            logger.debug("Error details:", exc_info=True)
            raise click.Abort from None

        diagnoses = analyze_yaml_stream(content, path)

        counter.update(diag.type for diag in diagnoses)
        output_formatter.update(content=content, diagnoses=diagnoses)

    logger.debug("Analysis completed. Found %d diagnoses.", sum(counter.values()))

    # write report
    with output_stream as stream:
        output_formatter.dump(stream)

    # finalize
    click.echo(counter.summary(), err=True)

    if counter.has_any_error():
        sys.exit(2)

    sys.exit(0)


def run_mcp() -> NoReturn:
    try:
        import tugboat.console.mcp
    except ImportError:
        raise click.UsageError(
            "MCP is not installed. To use this feature, please install Tugboat with the 'mcp' extra."
        ) from None

    tugboat.console.mcp.server.run()
    sys.exit(0)
