import io
import os

from tugboat.console.utils import VirtualPath, format_loc


class TestFormatLoc:
    def test(self):
        assert format_loc(["a", "b", "c"]) == ".a.b.c"
        assert format_loc(()) == "."


class TestVirtualPath:
    def test(self):
        stream = io.StringIO("content")

        path = VirtualPath("foo", stream)
        assert isinstance(path, os.PathLike)

        assert path.name == "foo"
        with path.open() as fd:
            assert fd.read() == "content"

        assert repr(path) == "VirtualPath('foo')"
