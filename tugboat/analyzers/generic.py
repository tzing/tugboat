from __future__ import annotations

import collections
import typing

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from tugboat.schemas import Artifact, Parameter, Template

    type NamedModel = Artifact | Parameter | Template


def report_duplicate_names(items: Sequence[NamedModel]) -> Iterator[tuple[int, str]]:
    # count the number of times each name appears
    names = collections.defaultdict(list)
    for idx, item in enumerate(items):
        if item.name:  # skip if name is empty
            names[item.name].append(idx)

    # report any names that appear more than once
    for name, indices in names.items():
        if len(indices) > 1:
            for idx in indices:
                yield idx, name
