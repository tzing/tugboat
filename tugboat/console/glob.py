from __future__ import annotations

import logging
import typing
import warnings
from pathlib import Path

from tugboat.types import PathPattern

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


logger = logging.getLogger(__name__)


def gather_paths(
    includes: Iterable[Path | PathPattern],
    excludes: Iterable[Path | PathPattern],
    follow_symlinks: bool = False,
) -> list[Path]:
    """
    Gather paths from the given include patterns and exclude patterns.
    """
    # collate all the paths to exclude
    exclude_files = {
        path for path in excludes if isinstance(path, Path) and path.is_file()
    }
    exclude_dirs = [
        path for path in excludes if isinstance(path, Path) and path.is_dir()
    ]
    exclude_patterns = [path for path in excludes if isinstance(path, PathPattern)]

    def _is_excluded(path: Path) -> bool:
        if path in exclude_files:
            return True
        if path in exclude_patterns:
            return True
        for exclude_dir in exclude_dirs:
            if exclude_dir in path.parents:
                return True
        return False

    # returns all the paths that are not excluded
    output = set()

    for path in _collect_file_paths(includes, follow_symlinks):
        if not _is_excluded(path):
            output.add(path)

    return list(output)


def _collect_file_paths(
    paths_or_patterns: Iterable[Path | PathPattern], follow_symlinks: bool = False
):
    for item in paths_or_patterns:
        if isinstance(item, PathPattern):
            logger.debug("Include pattern '%s'", item)
            if follow_symlinks:
                warnings.warn(
                    "Symlinks are not followed when using path patterns.",
                    UserWarning,
                    stacklevel=1,
                )
            yield from item.iglob(recursive=True, include_hidden=True)

        elif item.is_file():
            logger.debug("Include file '%s'", item)
            yield item

        elif item.is_dir():
            logger.debug("Include directory '%s'", item)
            yield from _list_yaml_in_dir(item, follow_symlinks)


def _list_yaml_in_dir(dir_path: Path, follow_symlinks: bool) -> Iterator[Path]:
    for root, _, files in dir_path.walk(follow_symlinks=follow_symlinks):
        for file in map(root.joinpath, files):
            if file.suffix in (".yaml", ".yml"):
                yield file
