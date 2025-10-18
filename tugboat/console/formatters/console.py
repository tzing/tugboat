from __future__ import annotations

import enum
import io
import textwrap
import typing

import click

from tugboat.console.formatters.base import OutputFormatter
from tugboat.settings import settings

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from typing import Any, Literal, TextIO

    from tugboat.engine import DiagnosisModel

    type Color = Literal[
        "black",
        "red",
        "green",
        "yellow",
        "blue",
        "magenta",
        "cyan",
        "white",
    ]


class ConsoleFormatter(OutputFormatter):

    def __init__(self):
        super().__init__()
        self.buf = io.StringIO()

    def update(self, *, content: str, diagnoses: Sequence[DiagnosisModel]) -> None:
        content_lines = content.splitlines()
        for diagnosis in diagnoses:
            self.append(
                content_lines=content_lines,
                diagnosis=diagnosis,
            )

    def dump(self, stream: TextIO) -> None:
        click.echo(
            self.buf.getvalue(),
            file=stream,
            color=settings.color,
            nl=False,
        )

    def append(  # noqa: C901
        self, *, content_lines: list[str], diagnosis: DiagnosisModel
    ) -> None:
        """
        Formats and appends a diagnosis to the internal buffer.

        Example output:

        ```none
        T01 Example error message
          @manifest.yaml:16:11 (demo-)
          @Template:templates/workflow.yaml

          14 |         command: [cowsay]
          15 |         args:
          16 |           - "{{ inputs.parameter.message }}"
             |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
             |              └ T01 at .spec.templates[0].container.args[0]

          Detail message explaining the error here.

          Do you mean: {{ inputs.parameters.message }}
        ```
        """
        # determine emphasis style
        match diagnosis.type:
            case "error" | "failure":
                emphasis = Style.Error
            case "warning":
                emphasis = Style.Warn

        # ---------------------------------------------------------------------
        # :PART: summary

        # > T01 Example error message
        self.buf.write(emphasis.fmt(diagnosis.code))
        self.buf.write(" ")
        self.buf.write(Style.Summary.fmt(diagnosis.summary))
        self.buf.write("\n")

        # > @manifest.yaml:16:11 (demo-)
        self.buf.write(Style.PathDelimiter.fmt("  @"))
        if diagnosis.extras.file:
            if diagnosis.extras.file.is_stdin:
                self.buf.write(Style.LocationStdin.fmt("<stdin>"))
            else:
                self.buf.write(diagnosis.extras.file.filepath)

        self.buf.write(Style.PathDelimiter.fmt(":"))
        self.buf.write(str(diagnosis.line))
        self.buf.write(Style.PathDelimiter.fmt(":"))
        self.buf.write(str(diagnosis.column))

        if diagnosis.extras.manifest and diagnosis.extras.manifest.name:
            self.buf.write(
                Style.ManifestName.fmt(f" ({diagnosis.extras.manifest.name})")
            )

        self.buf.write("\n")

        # > @Template:templates/workflow.yaml
        if diagnosis.extras.helm:
            self.buf.write(Style.PathDelimiter.fmt("  @Template:"))
            self.buf.write(diagnosis.extras.helm.template)
            self.buf.write("\n")

        self.buf.write("\n")

        # ---------------------------------------------------------------------
        # :PART: code snippet
        max_line_number = diagnosis.line + settings.console_output.snippet_lines_behind
        lncw = len(str(max_line_number - 1)) + 2  # line number column width

        for line_no, line_text in get_lines_near(content_lines, diagnosis.line):
            # code snippet lines
            # > 15 |         args:
            # > 16 |           - "{{ inputs.parameter.message }}"
            self.buf.write(Style.LineNumber.fmt(f"{line_no:{lncw}} | "))
            self.buf.write(line_text)
            self.buf.write("\n")

            # the emphasis line(s)
            if line_no == diagnosis.line:
                # indent: line number column + " | "
                indent = Style.LineNumber.fmt(" " * lncw + " | ")

                # draw underline if possible
                # >    ^^^^^^^^^
                if rng := calc_highlight_range(
                    line_text,
                    offset=diagnosis.column - 1,
                    substr=diagnosis.input,
                ):
                    col_start, col_end = rng
                    indent += " " * col_start

                    self.buf.write(indent)
                    self.buf.write(emphasis.fmt("^" * (col_end - col_start)))
                    self.buf.write("\n")

                else:
                    indent += " " * max(diagnosis.column - 1, 0)

                # draw position indicator
                # >    └ T01 at .spec.templates[0].container.args[0]
                self.buf.write(indent)
                self.buf.write(emphasis.fmt(f"└ {diagnosis.code}"))
                self.buf.write(Style.LocationDelimiter.fmt(" at "))
                self.buf.write(Style.Location.fmt(diagnosis.loc_path))
                self.buf.write("\n")

        # ---------------------------------------------------------------------
        # :PART: detail message
        if diagnosis.msg:
            self.buf.write("\n")
            self.buf.write(textwrap.indent(diagnosis.msg, "  "))
            self.buf.write("\n")

        # ---------------------------------------------------------------------
        # :PART: suggestion
        if diagnosis.fix:
            self.buf.write("\n")
            self.buf.write("  ")
            self.buf.write(Style.DoYouMean.fmt("Do you mean: "))

            if "\n" in diagnosis.fix:
                self.buf.write("|-\n")

                for line in diagnosis.fix.splitlines():
                    self.buf.write("  ")
                    self.buf.write(Style.Suggestion.fmt(line))
                    self.buf.write("\n")
            else:
                self.buf.write(Style.Suggestion.fmt(diagnosis.fix))
                self.buf.write("\n")

        self.buf.write("\n")  # separate entries with a blank line


class Style(enum.StrEnum):

    fg: Color | None
    bg: Color | None
    bold: bool | None
    dim: bool | None
    underline: bool | None

    def __new__(
        cls,
        value: str,
        fg: Color | None = None,
        bg: Color | None = None,
        bold: bool | None = None,
        dim: bool | None = None,
        underline: bool | None = None,
    ):
        obj = str.__new__(cls)
        obj._value_ = value
        obj.fg = fg
        obj.bg = bg
        obj.bold = bold
        obj.dim = dim
        obj.underline = underline
        return obj

    def fmt(self, text: Any) -> str:
        return click.style(
            str(text),
            fg=self.fg,
            bg=self.bg,
            bold=self.bold,
            dim=self.dim,
            underline=self.underline,
        )

    # fmt: off
    #                   value------- fg------  bg--- bold- dim-- underline
    DoYouMean =         enum.auto(), "cyan"
    Error =             enum.auto(), "red",    None, True
    LineNumber =        enum.auto(), None,     None, None, True
    Location =          enum.auto(), "cyan"
    LocationDelimiter = enum.auto(), None,     None, None, True
    LocationStdin =     enum.auto(), None,     None, True, True
    ManifestName =      enum.auto(), "blue"
    PathDelimiter =     enum.auto(), "cyan"
    Suggestion =        enum.auto(), None,     None, None, None, True
    Summary =           enum.auto(), None,     None, True
    Warn =              enum.auto(), "yellow", None, True


def get_lines_near(content: list[str], focus_line: int) -> Iterator[tuple[int, str]]:
    lines_ahead = settings.console_output.snippet_lines_ahead
    lines_behind = settings.console_output.snippet_lines_behind

    focus_line -= 1  # 1-based to 0-based
    line_starting = max(0, focus_line - lines_ahead)
    line_ending = min(len(content), focus_line + lines_behind)

    yield from enumerate(content[line_starting : line_ending + 1], line_starting + 1)


def calc_highlight_range(line: str, offset: int, substr: Any) -> tuple[int, int] | None:
    if substr is None:
        return  # early escape when substr value not given

    value = str(substr)
    if not value.strip():
        return  # prevent highlighting empty line

    try:
        col_start = line.index(value, offset)
    except ValueError:
        return

    col_end = col_start + len(value)
    return col_start, col_end
