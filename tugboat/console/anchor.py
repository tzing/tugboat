from __future__ import annotations

import io
import os
import random
import sys
import textwrap
import typing
from dataclasses import dataclass, field

import click

from tugboat.version import __version__

if typing.TYPE_CHECKING:
    from typing import NoReturn


def print_anchor() -> NoReturn:
    from tugboat._vendor.lolcat import LolCat, stdoutWin

    # build image
    ANCHOR = r"""
           _
          (_)       ______            __                __
        <--|-->    /_  __/_  ______ _/ /_  ____  ____ _/ /_
       _   |   _    / / / / / / __ `/ __ \/ __ \/ __ `/ __/
      `\__/ \__/`  / / / /_/ / /_/ / /_/ / /_/ / /_/ / /_
        `-. .-'   /_/  \__,_/\__, /_.___/\____/\__,_/\__/  {version}
           '                /____/
    """

    image = textwrap.dedent(ANCHOR).format(version=__version__).strip("\n")

    # setup lolcat
    @dataclass
    class _Option:

        os: int = field(default_factory=lambda: random.randint(0, 256))
        mode: int = field(default_factory=detect_mode)

        animate: bool = False
        force: bool = False
        freq: float = 0.1
        spread: float = 3.0

    options = _Option()

    # print image
    with io.StringIO(image) as input_buffer, io.StringIO() as output_buffer:
        if os.name == "nt":
            output = stdoutWin()
            output.output = output_buffer
        else:
            output = output_buffer

        lolcat = LolCat(mode=options.mode, output=output)

        input_buffer.seek(0)
        lolcat.cat(input_buffer, options)

        click.echo(output_buffer.getvalue(), nl=False)

    sys.exit(0)


def detect_mode():
    from tugboat._vendor.termcolors import ColorSupport, check_supported_colors

    match check_supported_colors():
        case ColorSupport.TRUE_COLOR | ColorSupport.ANSI_256:
            return 256
        case ColorSupport.BASIC:
            return 16

    return 8  # fallback to 8 colors; the lolcat library does not support no colors
