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
