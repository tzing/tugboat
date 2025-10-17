from __future__ import annotations

import enum
import io
import re
import typing
import urllib.parse
from dataclasses import dataclass

from tugboat.console.formatters.base import OutputFormatter

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from re import Match
    from typing import TextIO

    from tugboat.engine import DiagnosisModel


class Command(enum.StrEnum):
    """GitHub Actions Workflow commands"""

    Warning = "warning"
    Error = "error"


class GitHubFormatter(OutputFormatter):
    """
    Outputs diagnoses as GitHub Actions workflow commands.

    See also
    --------
    `Workflow commands for GitHub Actions
    <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands>`_
    """

    def __init__(self):
        super().__init__()
        self.commands: list[IssueCommand] = []

    def update(self, *, content: str, diagnoses: Sequence[DiagnosisModel]) -> None:
        for diagnosis in diagnoses:
            match diagnosis.type:
                case "error" | "failure":
                    command = Command.Error
                case "warning":
                    command = Command.Warning

            file = None
            if diagnosis.extras.file:
                file = diagnosis.extras.file.filepath

            title = diagnosis.code
            if diagnosis.summary:
                title += f" ({diagnosis.summary})"

            self.commands.append(
                IssueCommand(
                    command=command,
                    file=file,
                    line=diagnosis.line,
                    title=title,
                    message=diagnosis.msg,
                )
            )

    def dump(self, stream: TextIO):
        for cmd in self.commands:
            stream.write(str(cmd))
            stream.write("\n")


@dataclass
class IssueCommand:

    command: Command
    file: str | None
    line: int
    title: str
    message: str

    def __str__(self) -> str:
        # https://github.com/actions/toolkit/blob/%40actions/cache%404.0.0/packages/core/src/command.ts#L53

        def _properties() -> Iterator[tuple[str, str]]:
            if self.file:
                yield "file", escape_properties(self.file)
            yield "line", str(self.line)
            yield "title", escape_properties(self.title)

        with io.StringIO() as buf:
            # command
            buf.write("::")
            buf.write(self.command.value)

            # properties
            first = True
            for key, value in _properties():
                if first:
                    buf.write(" ")
                else:
                    buf.write(",")
                buf.write(key)
                buf.write("=")
                buf.write(value)
                first = False

            buf.write("::")

            # message
            buf.write(escape_message(self.message))

            return buf.getvalue()


def escape_properties(s: str) -> str:
    # https://github.com/actions/toolkit/blob/%40actions/cache%404.0.0/packages/core/src/command.ts#L87
    return re.sub(r"[\n\r%,:]+", _quote, s)


def escape_message(s: str) -> str:
    # https://github.com/actions/toolkit/blob/%40actions/cache%404.0.0/packages/core/src/command.ts#L80
    return re.sub(r"[\n\r%]+", _quote, s)


def _quote(m: Match[str]) -> str:
    return urllib.parse.quote(m.group(0))
