from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from collections.abc import Sequence


def format_loc(loc: Sequence[str | int]) -> str:
    return "." + ".".join(map(str, loc))
