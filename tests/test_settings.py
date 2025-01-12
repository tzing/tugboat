from pathlib import Path

import pytest
from pydantic import ValidationError

from tugboat.settings import Settings
from tugboat.types import PathPattern


class TestSettings:

    def test_env_var(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TUGBOAT_COLOR", "true")
        monkeypatch.setenv("TUGBOAT_CONSOLE_OUTPUT__SNIPPET_LINES_AHEAD", "99")

        settings = Settings()
        assert settings.color is True
        assert settings.console_output.snippet_lines_ahead == 99

    def test_toml(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        toml_file = tmp_path / ".tugboat.toml"
        toml_file.write_text(
            """
            color = false

            [console_output]
            snippet_lines_ahead = 100
            snippet_lines_behind = 101
            """
        )

        (tmp_path / "foo").mkdir()
        monkeypatch.chdir(tmp_path / "foo")

        settings = Settings()
        assert settings.color is False
        assert settings.console_output.snippet_lines_ahead == 100
        assert settings.console_output.snippet_lines_behind == 101

    def test_order(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        toml_file = tmp_path / "pyproject.toml"
        toml_file.write_text(
            """
            [tool.tugboat]
            color = false

            [tool.tugboat.console_output]
            snippet_lines_ahead = 100
            snippet_lines_behind = 101
            """
        )
        monkeypatch.chdir(tmp_path)

        monkeypatch.setenv("tugboat_console_output__snippet_lines_ahead", "99")

        settings = Settings(color=True)
        assert settings.color is True
        assert settings.console_output.snippet_lines_ahead == 99
        assert settings.console_output.snippet_lines_behind == 101

    def test_include(self):
        settings = Settings.model_validate({"include": [__file__, "foobar"]})

        item1, item2 = settings.include
        assert isinstance(item1, Path)
        assert isinstance(item2, PathPattern)

    def test_reject_dash(self):
        with pytest.raises(ValidationError):
            Settings(include=["foo", "-"])
        with pytest.raises(ValidationError):
            Settings(exclude=["-"])
