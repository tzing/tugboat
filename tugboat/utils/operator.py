from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from tugboat.types import Diagnosis


def prepend_loc(
    prefix: Sequence[str | int], iterable: Iterable[Diagnosis]
) -> Iterable[Diagnosis]:
    """Prepend the path to the location of each diagnosis in the iterable."""

    def _prepend(diagnoses: Diagnosis) -> Diagnosis:
        diagnoses["loc"] = (*prefix, *diagnoses.get("loc", []))
        return diagnoses

    return map(_prepend, iterable)
