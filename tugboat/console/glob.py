from __future__ import annotations

import logging
import typing
import warnings
from pathlib import Path

from tugboat.types import GlobPath

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from os import PathLike


logger = logging.getLogger(__name__)


def gather_paths(
    includes: Iterable[Path | GlobPath],
    excludes: Iterable[Path | GlobPath],
    follow_symlinks: bool = False,
) -> list[Path]:
    """
    Gather paths from the given include patterns and exclude patterns.
    """
    exclude_list = PathList(excludes)

    output = set()
    for item in includes:
        for file in yield_files(item, follow_symlinks=follow_symlinks):
            if file not in exclude_list:
                output.add(file)

    return list(output)


class PathList:

    def __init__(self, paths: Iterable[Path | GlobPath]):
        self.files = {
            path for path in paths if isinstance(path, Path) and path.is_file()
        }
        self.dirs = {path for path in paths if isinstance(path, Path) and path.is_dir()}

        # note - must be a list, need to run __eq__ on each item
        self.patterns = [path for path in paths if isinstance(path, GlobPath)]

    def __contains__(self, p: PathLike) -> bool:
        path = Path(p).resolve()
        if path in self.files:
            return True
        if any(path.is_relative_to(dir_) for dir_ in self.dirs):
            return True
        if path in self.patterns:
            return True
        return False


def yield_files(path: Path | GlobPath, follow_symlinks: bool = False) -> Iterator[Path]:
    if isinstance(path, GlobPath):
        logger.debug("Include glob pattern: %s", path)
        if follow_symlinks:
            warnings.warn(
                "Symlinks are not followed when using path patterns.",
                UserWarning,
                stacklevel=1,
            )
        yield from path.iglob(recursive=True, include_hidden=True)

    elif path.is_file():
        logger.debug("Include file: %s", path)
        yield path

    elif path.is_dir():
        logger.debug("Include directory: %s", path)
        for root, _, files in path.walk(follow_symlinks=follow_symlinks):
            for file in map(root.joinpath, files):
                if file.suffix in (".yaml", ".yml"):
                    yield file
