import io
import os

import pytest

from tugboat.console.utils import CachedStdin, format_loc


class TestFormatLoc:
    def test(self):
        assert format_loc(["a", "b", "c"]) == ".a.b.c"
        assert format_loc(()) == "."


class TestStdinPath:

    def test(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("sys.stdin", io.StringIO("foo"))

        path = CachedStdin()
        assert isinstance(path, os.PathLike)

        assert path.name == "<stdin>"

        with path.open() as fd:
            assert fd.read() == "foo"
        with path.open() as fd:
            assert fd.read() == "foo"  # should be cached

        assert path.is_file()
        assert not path.is_dir()
