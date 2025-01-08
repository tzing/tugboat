from __future__ import annotations

import io
import textwrap
import typing

import click

from tugboat.console.outputs.base import OutputBuilder
from tugboat.console.utils import format_loc
from tugboat.settings import settings

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path
    from typing import Any, TextIO

    from tugboat.analyze import AugmentedDiagnosis


class ConsoleOutputBuilder(OutputBuilder):

    def __init__(self):
        super().__init__()
        self._buffer = io.StringIO()

    def update(
        self, *, path: Path, content: str, diagnoses: Sequence[AugmentedDiagnosis]
    ) -> None:
        for diagnosis in diagnoses:
            self.report_diagnosis(path=path, content=content, diagnosis=diagnosis)

    def writeline(self, *values):
        print(*values, sep="", file=self._buffer)

    def report_diagnosis(
        self, *, path: Path, content: str, diagnosis: AugmentedDiagnosis
    ):
        match diagnosis["type"]:
            case "error" | "failure":
                emphasis = {"fg": "red", "bold": True}
            case "skipped":
                emphasis = {"fg": "yellow", "bold": True}
            case _:
                emphasis = {"fg": "magenta", "bold": True}

        # PART/ summary line
        self.writeline(
            click.style(path, bold=True),
            click.style(":", fg="cyan"),
            click.style(diagnosis["line"]),
            click.style(":", fg="cyan"),
            click.style(diagnosis["column"]),
            click.style(":", fg="cyan"),
            " ",
            click.style(diagnosis["code"], **emphasis),
            " ",
            diagnosis["summary"],
        )
        self.writeline()

        # PART/ code snippet
        content_lines = content.splitlines()

        # calculate the width of the line numbers
        max_line_number = (
            diagnosis["line"] + settings.console_output.snippet_lines_behind
        )
        line_number_width = len(str(max_line_number - 1)) + 1
        line_number_delimiter = click.style(" | ", dim=True)

        # print the code snippet
        for line_no, line in get_lines_near(content_lines, diagnosis["line"]):
            # general case: print the line number and the line
            self.writeline(
                click.style(f"{line_no:{line_number_width}}", dim=True),
                line_number_delimiter,
                line,
            )

            # if this is the line with the error, print additional information
            if line_no == diagnosis["line"]:
                # will still print the delimiter, but the line number will be empty
                padding = " " * line_number_width + line_number_delimiter

                # if possible, calculate the range to highlight, and print the underline
                if range_ := _calc_highlight_range(
                    line=line,
                    offset=diagnosis["column"] - 1,
                    input_=diagnosis["input"],
                ):
                    col_start, col_end = range_
                    padding += " " * col_start

                    self.writeline(
                        padding,
                        click.style("^" * (col_end - col_start), **emphasis),
                    )

                else:
                    padding += " " * max(diagnosis["column"] - 1, 0)

                # print the caret
                self.writeline(
                    padding,
                    click.style(f"└ {diagnosis["code"]}", **emphasis),
                    click.style(" at ", dim=True),
                    click.style(format_loc(diagnosis["loc"]), fg="cyan"),
                    click.style(" in ", dim=True),
                    click.style(diagnosis["manifest"] or "<unknown>", fg="blue"),
                )

        self.writeline()

        # PART/ details
        if details := diagnosis["msg"]:
            self.writeline(textwrap.indent(details, " " * (line_number_width + 1)))
            self.writeline()

        # PART/ suggestion
        if fix := diagnosis["fix"]:
            self.writeline(
                " " * (line_number_width + 1),
                click.style("Do you mean:", fg="cyan", bold=True),
                " ",
                click.style(fix, underline=True),
            )
            self.writeline()

    def dump(self, stream: TextIO) -> None:
        click.echo(
            self._buffer.getvalue(),
            file=stream,
            color=settings.color,
            nl=False,
        )


def get_lines_near(content: list[str], focus_line: int) -> Iterator[tuple[int, str]]:
    snippet_lines_ahead = settings.console_output.snippet_lines_ahead
    snippet_lines_behind = settings.console_output.snippet_lines_behind

    focus_line -= 1  # 1-based to 0-based
    line_starting = max(0, focus_line - snippet_lines_ahead)
    line_ending = min(len(content), focus_line + snippet_lines_behind)

    yield from enumerate(content[line_starting : line_ending + 1], line_starting + 1)


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
