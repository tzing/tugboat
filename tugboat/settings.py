from __future__ import annotations

import itertools
import typing
from pathlib import Path
from typing import Literal

import pydantic_settings
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if typing.TYPE_CHECKING:
    from pydantic_settings import PydanticBaseSettingsSource


class ConsoleOutputSettings(BaseSettings):
    """Settings for the console output."""

    snippet_lines_ahead: int = 2
    """Number of lines to show before the line with the issue."""

    snippet_lines_behind: int = 2
    """Number of lines to show after the line with the issue."""


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_prefix="tugboat_",
        extra="ignore",
        nested_model_default_partial_update=True,
        pyproject_toml_table_header=("tool", "tugboat"),
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            pydantic_settings.TomlConfigSettingsSource(
                settings_cls, _find_config(".tugboat.toml")
            ),
            pydantic_settings.PyprojectTomlConfigSettingsSource(
                settings_cls, _find_config("pyproject.toml")
            ),
        )

    color: bool | None = None
    """Colorize the output. If None, the output is colorized if the output is a terminal."""

    console_output: ConsoleOutputSettings = Field(default_factory=ConsoleOutputSettings)
    """Settings for the console output."""

    follow_symlinks: bool = False
    """Follow symbolic links when checking directories."""

    output_format: Literal["console", "junit"] = "console"
    """Output serialization format."""


def _find_config(name: str) -> Path | None:
    cwd = Path.cwd()
    for dir_ in itertools.chain([cwd], cwd.parents):
        path = dir_ / name
        if path.is_file():
            return path


settings = Settings()
