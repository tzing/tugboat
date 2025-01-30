from tugboat.utils.humanize import join_with_and, join_with_or


class TestJoinItems:
    def test_single(self):
        assert join_with_and(["foo"]) == "'foo'"

    def test_two(self):
        assert join_with_and(["foo", "bar"], quote=False) == "foo and bar"

    def test_three(self):
        assert join_with_or(["foo", "bar", "baz"]) == "'foo', 'bar' or 'baz'"

    def test_empty(self):
        assert join_with_and([]) == "(none)"
