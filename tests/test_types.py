import os
from pathlib import Path

import pytest
from dirty_equals import IsInstance
from pydantic import BaseModel

from tugboat.types import GlobPath, PathLike


class TestPathLike:

    def test_python_compatability(self):
        path = PathLike("foo")
        assert os.fspath(path) == "foo"
        assert isinstance(path, os.PathLike)
        assert repr(path) == "PathLike('foo')"
        assert str(path) == "foo"

    def test_pydantic_compatability(self):
        class Model(BaseModel):
            x: PathLike

        model = Model.model_validate({"x": "foo"})
        assert isinstance(model.x, PathLike)
        assert isinstance(model.x, os.PathLike)

        assert model.model_dump() == {"x": IsInstance(PathLike)}
        assert model.model_dump_json() == '{"x":"foo"}'


class TestGlobPath:

    def test_match_1(self):
        pp = GlobPath("foo*")

        assert pp == "foo"
        assert pp == Path("foo")
        assert pp == GlobPath("foo*")

        assert pp != "bar"
        assert pp != GlobPath("foo/*bar")

    def test_match_2(self):
        pp = GlobPath("**/*.yaml")
        assert pp == "foo.yaml"
        assert pp == Path("bar/foo.yaml")
        assert pp != "foo.YAML"

    def test_iglob_1(self, fixture_dir: Path):
        sample_workflow = fixture_dir / "sample-workflow.yaml"

        pattern = GlobPath(fixture_dir / "*.yaml")
        assert sample_workflow in list(pattern.iglob())

    def test_iglob_2(self):
        this_dir = Path(__file__).parent

        pattern = GlobPath(this_dir / "**" / "*.py")
        assert Path(__file__) in list(pattern.iglob(recursive=True))

    def test_failed(self):
        with pytest.raises(ValueError, match="Pattern 'foo' is not a glob pattern"):
            GlobPath("foo")
