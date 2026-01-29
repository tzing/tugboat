from __future__ import annotations

import enum
import io
import textwrap
import typing
from dataclasses import dataclass

import click

from tugboat.console.formatters.base import OutputFormatter
from tugboat.settings import settings

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from typing import Any, Literal, TextIO

    from tugboat.engine import DiagnosisModel
    from tugboat.settings import ConsoleOutputSettings

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
        snippet = Snippet(content.splitlines())
        for diagnosis in diagnoses:
            self.buf.write(
                str(
                    DiagnosticMessageBuilder(
                        diagnosis=diagnosis,
                        snippet=snippet,
                        settings=settings.console_output,
                    )
                )
            )
            self.buf.write("\n")

    def dump(self, stream: TextIO) -> None:
        click.echo(
            self.buf.getvalue(),
            file=stream,
            color=settings.color,
            nl=False,
        )


@dataclass
class DiagnosticMessageBuilder:

    diagnosis: DiagnosisModel
    snippet: Snippet
    settings: ConsoleOutputSettings

    @property
    def emphasis(self) -> Style:
        match self.diagnosis.type:
            case "error" | "failure":
                return Style.Error
            case "warning":
                return Style.Warn
        return Style.Error

    def __str__(self) -> str:
        """
        Formats the diagnosis to rich text.

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
        with io.StringIO() as buf:
            buf.write(self.summary())
            buf.write("\n")
            buf.write(self.code_area())

            if details := self.details():
                buf.write("\n")
                buf.write(details)

            if suggestion := self.suggestion():
                buf.write("\n")
                buf.write(suggestion)

            return buf.getvalue()

    def summary(self) -> str:
        with io.StringIO() as buf:
            # Headline
            # > T01 Example error message
            buf.write(self.emphasis.fmt(self.diagnosis.code))
            buf.write(" ")
            buf.write(Style.Summary.fmt(self.diagnosis.summary))
            buf.write("\n")

            # Path, location, manifest
            # > @manifest.yaml:16:11 (demo-)
            buf.write(Style.PathDelimiter.fmt("  @"))
            if self.diagnosis.extras.file:
                if self.diagnosis.extras.file.is_stdin:
                    buf.write(Style.LocationStdin.fmt("<stdin>"))
                else:
                    buf.write(self.diagnosis.extras.file.filepath)

            buf.write(Style.PathDelimiter.fmt(":"))
            buf.write(str(self.diagnosis.line))
            buf.write(Style.PathDelimiter.fmt(":"))
            buf.write(str(self.diagnosis.column))

            if self.diagnosis.extras.manifest and self.diagnosis.extras.manifest.name:
                buf.write(
                    Style.ManifestName.fmt(f" ({self.diagnosis.extras.manifest.name})")
                )

            buf.write("\n")

            # Helm template info
            # > @Template:templates/workflow.yaml
            if self.diagnosis.extras.helm:
                buf.write(Style.PathDelimiter.fmt("  @Template:"))
                buf.write(self.diagnosis.extras.helm.template)
                buf.write("\n")

            return buf.getvalue()

    def code_area(self) -> str:
        max_line_number = self.diagnosis.line + self.settings.snippet_lines_behind
        lncw = len(str(max_line_number - 1)) + 2  # line number column width

        with io.StringIO() as buf:
            # code snippet before (and including) the issue
            # > 15 |         args:
            # > 16 |           - "{{ inputs.parameter.message }}"
            for line_no, line_text in self.snippet.lines_between(
                start=self.diagnosis.line - self.settings.snippet_lines_ahead,
                last=self.diagnosis.line,
            ):
                buf.write(Style.LineNumber.fmt(f"{line_no:{lncw}} | "))
                buf.write(line_text)
                buf.write("\n")

            # markers for the issue line
            # marker prefix: line number column + " | "
            prefix = Style.LineNumber.fmt(" " * lncw + " | ")

            # draw underline if possible
            # >    ^^^^^^^^^
            if rng := calc_highlight_range(
                self.snippet[self.diagnosis.line],
                offset=self.diagnosis.column - 1,
                substr=self.diagnosis.input,
            ):
                col_start, col_end = rng
                prefix += " " * col_start

                buf.write(prefix)
                buf.write(self.emphasis.fmt("^" * (col_end - col_start)))
                buf.write("\n")

            else:
                prefix += " " * max(self.diagnosis.column - 1, 0)

            # draw position indicator
            # >    └ T01 at .spec.templates[0].container.args[0]
            buf.write(prefix)
            buf.write(self.emphasis.fmt(f"└ {self.diagnosis.code}"))
            buf.write(Style.LocationDelimiter.fmt(" at "))
            buf.write(Style.Location.fmt(self.diagnosis.loc_path))
            buf.write("\n")

            # code snippet after the issue
            for line_no, line_text in self.snippet.lines_between(
                start=self.diagnosis.line + 1,
                last=self.diagnosis.line + self.settings.snippet_lines_behind,
            ):
                buf.write(Style.LineNumber.fmt(f"{line_no:{lncw}} | "))
                buf.write(line_text)
                buf.write("\n")

            return buf.getvalue()

    def details(self) -> str:
        if not self.diagnosis.msg:
            return ""
        return textwrap.indent(self.diagnosis.msg, "  ") + "\n"

    def suggestion(self) -> str:
        if not self.diagnosis.fix:
            return ""

        with io.StringIO() as buf:
            buf.write("  ")
            buf.write(Style.DoYouMean.fmt("Do you mean: "))

            if "\n" in self.diagnosis.fix:
                buf.write("|-\n")
                for line in self.diagnosis.fix.splitlines():
                    buf.write("  ")
                    buf.write(Style.Suggestion.fmt(line))
                    buf.write("\n")
            else:
                buf.write(Style.Suggestion.fmt(self.diagnosis.fix))
                buf.write("\n")

            return buf.getvalue()


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


@dataclass
class Snippet:

    lines: list[str]

    def __getitem__(self, lineno: int) -> str:
        """Gets the line at the given 1-based line number."""
        if lineno > len(self.lines):
            return ""
        return self.lines[lineno - 1]

    def lines_between(self, start: int, last: int) -> Iterator[tuple[int, str]]:
        """Yields lines between the given 1-based line numbers (inclusive)."""
        start = max(start, 1)
        yield from enumerate(self.lines[start - 1 : last], start)


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
