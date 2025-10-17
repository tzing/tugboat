from __future__ import annotations

import itertools
import os
import typing
from pathlib import Path
from typing import Literal

import pydantic_settings
from pydantic import (
    DirectoryPath,
    Field,
    FilePath,
    ValidationError,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from tugboat.types import GlobPath

if typing.TYPE_CHECKING:
    from typing import Any

    from pydantic_settings import PydanticBaseSettingsSource


type _PathSpec = FilePath | DirectoryPath | GlobPath


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

    exclude: list[_PathSpec] = Field(default_factory=list)
    """List of paths or patterns to exclude from the check."""

    include: list[_PathSpec] = Field(default=[Path.cwd()])
    """List of paths or patterns to include in the check."""

    follow_symlinks: bool = False
    """Follow symbolic links when checking directories."""

    output_format: Literal["console", "junit", "github"] = "console"
    """Output serialization format."""

    @field_validator("color")
    @classmethod
    def _validate_color_(cls, value: bool | None) -> bool | None:
        if os.getenv("FORCE_COLOR"):  # https://force-color.org/
            return True
        if os.getenv("NO_COLOR"):  # https://no-color.org/
            return False
        return value

    @field_validator("include", "exclude", mode="wrap")
    @classmethod
    def _validate_path_(
        cls, value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ):
        try:
            return handler(value)
        except ValidationError as exc:
            error_items = {}
            for error in exc.errors():
                # the second item is the annotation from type validator
                idx, _ = error["loc"]
                error_items[idx] = error["input"]

            line_errors = []
            for idx, input_ in error_items.items():
                line_errors.append(
                    {
                        "type": "value_error",
                        "loc": (idx,),
                        "input": input_,
                        "ctx": {"error": ValueError("input is not a valid path spec.")},
                    }
                )

            raise ValidationError.from_exception_data(
                typing.cast("str", info.field_name),
                line_errors,
            ) from exc


def _find_config(name: str) -> Path | None:
    cwd = Path.cwd()
    for dir_ in itertools.chain([cwd], cwd.parents):
        path = dir_ / name
        if path.is_file():
            return path


settings = Settings()
