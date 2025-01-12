import os
from pathlib import Path

from pydantic import TypeAdapter

from tugboat.types import PathPattern


class TestPathPattern:

    def test_pydantic(self):
        ta = TypeAdapter(PathPattern)

        obj = ta.validate_python("foo")
        assert isinstance(obj, PathPattern)
        assert obj.pattern == os.path.realpath("foo")

        assert isinstance(ta.validate_python(obj), PathPattern)

    def test_match_1(self):
        pp = PathPattern("foo")
        assert pp == "foo"
        assert pp == Path("foo")
        assert pp != "fooo"
        assert pp == PathPattern("foo")
        assert pp != PathPattern("foo/bar")

    def test_match_2(self):
        pp = PathPattern("**/*.yaml")
        assert pp == "foo.yaml"
        assert pp == Path("bar/foo.yaml")
        assert pp != "foo.YAML"

    def test_repr(self):
        pp = PathPattern("foo")
        assert isinstance(repr(pp), str)

    def test_iglob_1(self, fixture_dir: Path):
        sample_workflow = fixture_dir / "sample-workflow.yaml"

        pattern = PathPattern(fixture_dir / "*.yaml")
        assert sample_workflow in list(pattern.iglob())

    def test_iglob_2(self):
        this_dir = Path(__file__).parent

        pattern = PathPattern(this_dir / "**" / "*.py")
        assert Path(__file__) in list(pattern.iglob(recursive=True))
