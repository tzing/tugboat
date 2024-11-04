from __future__ import annotations

import functools
import textwrap
import typing

import click

from tugboat.console.utils import format_loc

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path
    from typing import IO

    from tugboat.analyze import ExtendedDiagnostic

LINES_AHEAD = 2
LINES_BEHIND = 2


def report(
    diagnostics: dict[Path, list[ExtendedDiagnostic]],
    stream: IO[str],
    color: bool | None,
) -> None:
    def _echo(*args, nl: bool = True):
        click.echo("".join(args), file=stream, color=color, nl=nl)

    for path, diags in diagnostics.items():
        for diag in diags:
            report_diagnostic(echo=_echo, file=path, diagnostic=diag)


def report_diagnostic(echo: Callable, file: Path, diagnostic: ExtendedDiagnostic):
    if diagnostic["type"] in ("error", "failure"):
        error_style = {"fg": "red", "bold": True}
    elif diagnostic["type"] == "skipped":
        error_style = {"fg": "yellow", "bold": True}
    else:
        error_style = {"fg": "magenta", "bold": True}

    # print the summary
    echo(
        click.style(file, bold=True),
        click.style(":", fg="cyan"),
        click.style(diagnostic["line"]),
        click.style(":", fg="cyan"),
        click.style(diagnostic["column"]),
        click.style(":", fg="cyan"),
        " ",
        click.style(diagnostic["code"], **error_style),
        " ",
        diagnostic["summary"],
    )

    echo()

    # print the code snippet
    line_number_width = len(str(diagnostic["line"] + LINES_BEHIND - 1)) + 1
    line_number_delimiter = click.style(" | ", dim=True)
    for ln, line in get_content_near(file, diagnostic["line"]):
        echo(
            click.style(f"{ln:{line_number_width}}", dim=True),
            line_number_delimiter,
            line,
        )

        if ln == diagnostic["line"]:
            line_prefix = " " * line_number_width + line_number_delimiter

            # calculate the indent before the caret
            # default to the column number, but if the input is present, use that instead
            indent_before_caret = " " * max(diagnostic["column"] - 1, 0)

            if diagnostic["input"] is not None and str(diagnostic["input"]) in line:
                col_start = line.index(str(diagnostic["input"]))
                col_end = col_start + len(str(diagnostic["input"]))
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
                click.style(f"└ {diagnostic["code"]}", **error_style),
                click.style(" at ", dim=True),
                click.style(format_loc(diagnostic["loc"]), fg="cyan"),
                click.style(" in ", dim=True),
                click.style(diagnostic["manifest"] or "<unknown>", fg="blue"),
            )

    echo()

    # print the details
    echo(textwrap.indent(diagnostic["msg"], " " * (line_number_width + 1)))
    echo()

    # print the suggestion
    if fix := diagnostic["fix"]:
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
    start = max(0, target_line - LINES_BEHIND)
    end = min(len(content), target_line + LINES_AHEAD)
    yield from enumerate(content[start:end], start + 1)


@functools.lru_cache(1)
def read_file(path: Path) -> str:
    return path.read_text()
