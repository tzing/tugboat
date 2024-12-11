from tugboat.console.utils import format_loc


class TestFormatLoc:
    def test(self):
        assert format_loc(["a", "b", "c"]) == ".a.b.c"
        assert format_loc(()) == "."
