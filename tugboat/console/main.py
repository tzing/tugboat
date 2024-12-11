from __future__ import annotations

import logging
import sys
import typing
from pathlib import Path

import click
import cloup
import colorlog

from tugboat.analyze import analyze_yaml
from tugboat.console.utils import VirtualPath, cached_read
from tugboat.version import __version__

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from tugboat.analyze import AugmentedDiagnosis

logger = logging.getLogger(__name__)


@cloup.command(
    context_settings={
        "help_option_names": ["-h", "--help"],
    }
)
@cloup.argument(
    "manifest",
    nargs=-1,
    type=cloup.path(),
    help="List of files or directories to check. Use '-' for stdin. [default: .]",
)
@cloup.option_group(
    "Output options",
    cloup.option(
        "--color",
        type=cloup.BOOL,
        help="Use colors in output. [default: auto]",
    ),
    cloup.option(
        "--output-format",
        type=cloup.Choice(["console", "junit"]),
        default="console",
        show_default=True,
        help="Output serialization format.",
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
    manifest: Sequence[Path],
    color: bool | None,
    output_format: str,
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

    # determine the inputs
    manifest_paths: list[Path] = []
    if "-" in map(str, manifest):
        if len(manifest) > 1:
            raise click.BadArgumentUsage(
                "Cannot read from stdin and file at the same time."
            )

        stdin = VirtualPath(sys.stdin.name, sys.stdin)
        manifest_paths += [typing.cast(Path, stdin)]

    else:
        for path in manifest:
            if path.is_dir():
                manifest_paths += find_yaml(path)
            else:
                manifest_paths += [path]

    if not manifest_paths:
        raise click.UsageError("No manifest found.")

    manifest_paths = sorted(manifest_paths)
    logger.info("Found %d manifest(s) to analyze.", len(manifest_paths))

    # analyze manifests
    diagnoses: dict[Path, list[AugmentedDiagnosis]] = {}
    for i, path in enumerate(manifest_paths, 1):
        logger.info("[%d/%d] Analyzing file %s", i, len(manifest_paths), path)
        try:
            content = cached_read(path)
        except Exception:
            logger.error("Failed to read file %s", path)
            logger.debug("Error details:", exc_info=True)
            raise click.Abort from None

        diagnoses[path] = analyze_yaml(content)

    logger.debug(
        "Analysis completed. Found %d diagnoses.",
        sum(map(len, diagnoses.values())),
    )

    # generate report
    generate_report(diagnoses, output_format, output_file, color)

    # finalize
    is_success = summarize(diagnoses)
    if not is_success:
        sys.exit(2)


def find_yaml(dirpath: Path) -> Iterator[Path]:
    for root, _, files in dirpath.walk(follow_symlinks=True):
        for name in files:
            path = root / name
            if path.suffix in (".yaml", ".yml"):
                yield path


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


def generate_report(
    diagnoses: dict[Path, list[AugmentedDiagnosis]],
    output_format: str,
    output_file: Path | None,
    color: bool | None,
) -> None:
    logger.info("Generating diagnostic report...")

    # open the output stream
    if output_file:
        output_stream = output_file.open("w")
    else:
        output_stream = sys.stdout

    # generate the report
    if output_format == "console":
        from tugboat.console.outputs.console import report

        report(diagnoses, output_stream, color)

    elif output_format == "junit":
        from tugboat.console.outputs.junit import report

        report(diagnoses, output_stream)

    # close the output stream
    if output_file:
        output_stream.close()


def summarize(aggregated_diagnoses: dict[Path, list[AugmentedDiagnosis]]) -> bool:
    """
    Summarize the diagnoses.
    Return a boolean indicating whether the checks passed or not.
    """
    counts = {
        "error": 0,
        "failure": 0,
        "skipped": 0,
    }

    for diagnoses in aggregated_diagnoses.values():
        for diagnosis in diagnoses:
            counts[diagnosis["type"]] = counts.get(diagnosis["type"], 0) + 1

    summary_parts = []
    if count := counts["error"]:
        summary_parts.append(f"{count} errors")
    if count := counts["failure"]:
        summary_parts.append(f"{count} failures")
    if count := counts["skipped"]:
        summary_parts.append(f"{count} skipped checks")

    if summary_parts:
        click.echo("Found " + ", ".join(summary_parts), err=True)
    else:
        click.echo("All passed!", err=True)

    return not any((counts["error"], counts["failure"]))
