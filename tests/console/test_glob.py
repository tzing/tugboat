from pathlib import Path

import pytest

from tugboat.console.glob import PathList, gather_paths, yield_files
from tugboat.types import GlobPath


class TestGatherPaths:

    @pytest.fixture
    def tmp_manifest_path(self, tmp_path: Path):
        (tmp_path / "file1.yaml").touch()
        (tmp_path / "dir1").mkdir()
        (tmp_path / "dir1" / "file2.yaml").touch()
        (tmp_path / "dir2").mkdir()
        (tmp_path / "dir2" / "file3.yaml").touch()
        return tmp_path

    def test_exclude_none(self, tmp_manifest_path: Path):
        paths = gather_paths([tmp_manifest_path], [])
        assert set(paths) == {
            tmp_manifest_path / "file1.yaml",
            tmp_manifest_path / "dir1" / "file2.yaml",
            tmp_manifest_path / "dir2" / "file3.yaml",
        }

    def test_exclude_file(self, tmp_manifest_path: Path):
        paths = gather_paths([tmp_manifest_path], [tmp_manifest_path / "file1.yaml"])
        assert set(paths) == {
            tmp_manifest_path / "dir1" / "file2.yaml",
            tmp_manifest_path / "dir2" / "file3.yaml",
        }

    def test_exclude_dir(self, tmp_manifest_path: Path):
        paths = gather_paths([tmp_manifest_path], [tmp_manifest_path / "dir1"])
        assert set(paths) == {
            tmp_manifest_path / "file1.yaml",
            tmp_manifest_path / "dir2" / "file3.yaml",
        }

    def test_exclude_pattern(self, tmp_manifest_path: Path):
        paths = gather_paths(
            [tmp_manifest_path], [GlobPath(tmp_manifest_path / "dir?" / "*.yaml")]
        )
        assert set(paths) == {
            tmp_manifest_path / "file1.yaml",
        }


class TestPathList:

    def test(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "file1.yaml").touch()
        (tmp_path / "dir1").mkdir()

        pl = PathList(
            [
                tmp_path / "file1.yaml",
                tmp_path / "dir1",
                GlobPath(tmp_path / "*.yaml"),
            ]
        )

        assert (tmp_path / "file1.yaml") in pl
        assert (tmp_path / "dir1" / "foo.yaml") in pl
        assert (tmp_path / "dir1" / "foo.txt") in pl
        assert (tmp_path / "file2.yaml") in pl

        assert (tmp_path / "file1.py") not in pl
        assert (tmp_path / "dir2" / "foo.txt") not in pl


class TestYieldFiles:

    def test_file(self):
        paths = list(yield_files(Path(__file__)))
        assert len(paths) == 1
        assert Path(__file__) in paths

    def test_directory(self, fixture_dir: Path):
        paths = list(yield_files(fixture_dir, follow_symlinks=False))
        assert (fixture_dir / "sample-workflow.yaml") in paths

    @pytest.mark.filterwarnings("ignore::UserWarning:tugboat.console.glob")
    def test_pattern(self, fixture_dir: Path):
        pattern = GlobPath(fixture_dir / "*.yaml")
        paths = list(yield_files(pattern, follow_symlinks=True))
        assert (fixture_dir / "sample-workflow.yaml") in paths
