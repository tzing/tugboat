from __future__ import annotations

import functools
import textwrap
import typing

import click

from tugboat.console.utils import format_loc

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path
    from typing import IO, Any

    from tugboat.analyze import AugmentedDiagnosis

LINES_AHEAD = 2
LINES_BEHIND = 2


def report(
    aggregated_diagnoses: dict[Path, list[AugmentedDiagnosis]],
    stream: IO[str],
    color: bool | None,
) -> None:
    def _echo(*args, nl: bool = True):
        click.echo("".join(args), file=stream, color=color, nl=nl)

    for path, diags in aggregated_diagnoses.items():
        for diag in diags:
            report_diagnosis(echo=_echo, file=path, diagnosis=diag)


def report_diagnosis(echo: Callable, file: Path, diagnosis: AugmentedDiagnosis):
    if diagnosis["type"] in ("error", "failure"):
        error_style = {"fg": "red", "bold": True}
    elif diagnosis["type"] == "skipped":
        error_style = {"fg": "yellow", "bold": True}
    else:
        error_style = {"fg": "magenta", "bold": True}

    # print the summary
    echo(
        click.style(file, bold=True),
        click.style(":", fg="cyan"),
        click.style(diagnosis["line"]),
        click.style(":", fg="cyan"),
        click.style(diagnosis["column"]),
        click.style(":", fg="cyan"),
        " ",
        click.style(diagnosis["code"], **error_style),
        " ",
        diagnosis["summary"],
    )

    echo()

    # print the code snippet
    line_number_width = len(str(diagnosis["line"] + LINES_BEHIND - 1)) + 1
    line_number_delimiter = click.style(" | ", dim=True)
    for ln, line in get_content_near(file, diagnosis["line"]):
        echo(
            click.style(f"{ln:{line_number_width}}", dim=True),
            line_number_delimiter,
            line,
        )

        if ln == diagnosis["line"]:
            line_prefix = " " * line_number_width + line_number_delimiter

            # calculate the indent before the caret
            # default to the column number, but if the input is present, use that instead
            indent_before_caret = " " * max(diagnosis["column"] - 1, 0)

            if range_ := _calc_highlight_range(
                line=line,
                offset=diagnosis["column"] - 1,
                input_=diagnosis["input"],
            ):
                col_start, col_end = range_
                indent_before_caret = " " * col_start

                # print the underline
                echo(
                    line_prefix,
                    indent_before_caret,
                    click.style("^" * (col_end - col_start), **error_style),
                )

            # print the caret
            echo(
                line_prefix,
                indent_before_caret,
                click.style(f"└ {diagnosis["code"]}", **error_style),
                click.style(" at ", dim=True),
                click.style(format_loc(diagnosis["loc"]), fg="cyan"),
                click.style(" in ", dim=True),
                click.style(diagnosis["manifest"] or "<unknown>", fg="blue"),
            )

    echo()

    # print the details
    echo(textwrap.indent(diagnosis["msg"], " " * (line_number_width + 1)))
    echo()

    # print the suggestion
    if fix := diagnosis["fix"]:
        echo(
            " " * (line_number_width + 1),
            click.style("Do you mean:", fg="cyan", bold=True),
            " ",
            click.style(fix, underline=True),
        )
        echo()


def get_content_near(file: Path, target_line: int) -> Iterator[tuple[int, str]]:
    target_line -= 1  # 1-based to 0-based
    content = read_file(file).splitlines()
    start = max(0, target_line - LINES_AHEAD)
    end = min(len(content), target_line + LINES_BEHIND)
    yield from enumerate(content[start : end + 1], start + 1)


@functools.lru_cache(1)
def read_file(path: Path) -> str:
    return path.read_text()


def _calc_highlight_range(line: str, offset: int, input_: Any):
    """
    Calculate the range to highlight in the line.
    """
    if input_ is None:
        return  # early escape if no value is provided

    value = str(input_)
    if not value.strip():
        return  # prevent highlighting empty strings

    try:
        col_start = line.index(value, offset)
    except ValueError:
        return

    col_end = col_start + len(value)
    return col_start, col_end
