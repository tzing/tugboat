#! /user/bin/env python3
"""
Checks how many colors are supported by the terminal.

Acknowledgements
================
The logic of this script is primarily based on the implementation found in:
- https://github.com/nodejs/node/blob/v24.2.0/lib/internal/tty.js
- https://github.com/chalk/supports-color
"""
from __future__ import annotations

__all__ = ["ColorSupport", "check_supported_colors"]

import enum
import os
import re
import sys
import typing

if typing.TYPE_CHECKING:
    from typing import TextIO


class ColorSupport(enum.Enum):
    """
    Enum for color support.
    """

    NONE = enum.auto()
    """No color support."""

    BASIC = enum.auto()
    """Basic color support (16 colors)."""

    ANSI_256 = enum.auto()
    """256 color support."""

    TRUE_COLOR = enum.auto()
    """True color support (24-bit, 16 million colors)."""


def check_supported_colors(stream: TextIO | None = None) -> ColorSupport:
    """
    Check how many colors are supported by the terminal.
    """
    # User specified behaviors
    match os.getenv("FORCE_COLOR"):  # https://force-color.org/
        case "" | "1" | "true":
            return ColorSupport.BASIC
        case "2":
            return ColorSupport.ANSI_256
        case "3":
            return ColorSupport.TRUE_COLOR

    if "NO_COLOR" in os.environ:  # https://no-color.org/
        return ColorSupport.NONE

    # dumb terminals
    if os.getenv("TERM") == "dumb":
        return ColorSupport.NONE

    # Azure DevOps
    if "TF_BUILD" in os.environ and "AGENT_NAME" in os.environ:
        return ColorSupport.BASIC

    # Check if the stream is a TTY
    if stream and not stream.isatty():
        return ColorSupport.NONE

    # Windows
    if sys.platform == "win32":
        if _has_env("ANSICON"):  # ANSICON
            return ColorSupport.TRUE_COLOR
        if _has_env("ConEmuANSI"):  # ConEmu
            return ColorSupport.ANSI_256

        version_info = sys.getwindowsversion()
        if version_info.major >= 10:  # Windows 10
            if version_info.build >= 14931:
                return ColorSupport.TRUE_COLOR
            if version_info.build >= 10586:
                return ColorSupport.ANSI_256

        return ColorSupport.BASIC

    # CI environments
    if _has_env("CI"):
        if _has_env("CIRCLECI", "GITEA_ACTIONS", "GITHUB_ACTIONS"):
            return ColorSupport.TRUE_COLOR
        if _has_env("APPVEYOR", "BUILDKITE", "DRONE", "GITLAB_CI", "TRAVIS"):
            return ColorSupport.ANSI_256

    # JetBrains TeamCity
    if _has_env("TEAMCITY_VERSION"):
        version_info = _split_version(os.getenv("TEAMCITY_VERSION", "0"))
        if version_info >= (9,):
            return ColorSupport.BASIC
        return ColorSupport.NONE

    # terminal emulators
    match os.getenv("TERM_PROGRAM"):
        case "Apple_Terminal":
            return ColorSupport.ANSI_256
        case "HyperTerm":
            return ColorSupport.TRUE_COLOR
        case "iTerm.app":
            version_info = _split_version(os.getenv("TERM_PROGRAM_VERSION", "0"))
            if version_info >= (3,):
                return ColorSupport.TRUE_COLOR
            return ColorSupport.ANSI_256
        case "MacTerm":
            return ColorSupport.TRUE_COLOR
        case "vscode":
            return ColorSupport.ANSI_256

    # $COLORTERM environment variable
    if os.getenv("COLORTERM") in ("truecolor", "24bit"):
        return ColorSupport.TRUE_COLOR

    # $TERM environment variable
    if term := os.getenv("TERM"):
        match term:
            case (
                "cons25"
                | "console"
                | "cygwin"
                | "dtterm"
                | "eterm"
                | "gnome"
                | "hurd"
                | "jfbterm"
                | "konsole"
                | "kterm"
                | "mlterm"
                | "putty"
                | "st"
            ):
                return ColorSupport.BASIC

            case "mosh" | "rxvt-unicode-24bit" | "terminator" | "xterm-kitty":
                return ColorSupport.TRUE_COLOR

        if any(keyword in term for keyword in ("truecolor", "24bit")):
            return ColorSupport.TRUE_COLOR

        term = term.lower()

        if term.endswith(("-256", "-256color")):
            return ColorSupport.ANSI_256

        if term.startswith(("rxvt", "screen", "vt100", "vt220", "xterm")):
            return ColorSupport.BASIC

        if any(
            keyword in term
            for keyword in ("ansi", "color", "cygwin", "direct", "linux")
        ):
            return ColorSupport.BASIC

        if re.match(r"con[0-9]*x[0-9]", term):
            return ColorSupport.BASIC

    if _has_env("COLORTERM"):
        return ColorSupport.BASIC

    # can't determine color support
    return ColorSupport.NONE


def _has_env(*names: str) -> bool:
    """Check if any of the given environment variable names exist."""
    return any(map(os.getenv, names))


def _split_version(v: str) -> tuple[int, ...]:
    """Split a version string into a tuple of integers."""
    return tuple(map(int, v.split(".")))


if __name__ == "__main__":
    print("Supported colors for stdout:", check_supported_colors(sys.stdout))
    print("Supported colors for stdout:", check_supported_colors(sys.stderr))
