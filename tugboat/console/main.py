from __future__ import annotations

import logging
import sys
import typing
from pathlib import Path

import click
import cloup
import colorlog

from tugboat.analyze import analyze_yaml
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
    "path",
    type=cloup.path(exists=True),
    nargs=-1,
    help="List of files or directories to check. [default: .]",
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
    path: Sequence[Path],
    color: bool | None,
    output_format: str,
    output_file: Path | None,
    verbose: int,
):
    """
    Linter to streamline your Argo Workflows with precision and confidence.
    """
    # setup logging
    setup_logging(verbose)
    logger.debug("Tugboat sets sail!")

    # check how many files to analyze
    target_files: list[Path] = []

    if not path:
        path = [Path(".")]

    for subpath in path:
        if subpath.is_dir():
            target_files += sorted(find_yaml(subpath))
        else:
            target_files.append(subpath)

    logger.info("Found %d YAML files to analyze.", len(target_files))

    if not target_files:
        logger.warning("No YAML file found.")
        raise click.Abort

    # analyze files
    diagnoses: dict[Path, list[AugmentedDiagnosis]] = {}
    for i, file_path in enumerate(target_files, 1):
        logger.info("[%d/%d] Analyzing file %s", i, len(target_files), file_path)
        try:
            manifest = file_path.read_text()
        except Exception:
            logger.error("Failed to read file %s", file_path)
            logger.debug("Error details:", exc_info=True)
            raise click.Abort from None

        diagnoses[file_path] = analyze_yaml(manifest)

    logger.debug(
        "Analysis completed. Found %d diagnoses.",
        sum(map(len, diagnoses.values())),
    )

    # generate report
    generate_report(diagnoses, output_format, output_file, color)

    # finalize
    summary, is_failed = summarize(diagnoses)

    print(summary, file=sys.stderr)

    if is_failed:
        sys.exit(2)


def find_yaml(dirpath: Path) -> Iterator[Path]:
    for root, _, files in dirpath.walk():
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


def summarize(
    aggregated_diagnoses: dict[Path, list[AugmentedDiagnosis]]
) -> tuple[str, bool]:
    """
    Summarize the diagnoses. Return a tuple of the summary message and a
    boolean indicating whether the diagnoses contain any error or failure.
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
        msg = "Found " + ", ".join(summary_parts)
    else:
        msg = "All passed!"

    is_failed = any((counts["error"], counts["failure"]))
    return msg, is_failed
