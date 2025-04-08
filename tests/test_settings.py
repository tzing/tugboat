from pathlib import Path

import pytest
from dirty_equals import IsPartialDict
from pydantic import ValidationError

from tugboat.settings import Settings
from tugboat.types import GlobPath


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

    def test_include_1(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "foo").mkdir()
        (tmp_path / "bar").touch()

        settings = Settings.model_validate({"include": ["foo", "bar", "foo*"]})

        assert len(settings.include) == 3
        assert isinstance(settings.include[0], Path)
        assert settings.include[0].is_dir()
        assert isinstance(settings.include[1], Path)
        assert settings.include[1].is_file()
        assert isinstance(settings.include[2], GlobPath)

    def test_include_2(self):
        with pytest.raises(ValidationError) as exc_info:
            Settings.model_validate({"include": ["no-such-file"]})

        assert exc_info.value.errors() == [
            IsPartialDict(
                {
                    "type": "value_error",
                    "loc": ("include", 0),
                    "msg": "Value error, input is not a valid path spec.",
                }
            )
        ]
