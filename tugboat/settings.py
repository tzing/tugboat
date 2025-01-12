from __future__ import annotations

import itertools
import typing
from pathlib import Path
from typing import Annotated, Literal

import pydantic_core.core_schema
import pydantic_settings
from pydantic import DirectoryPath, Field, FilePath, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from tugboat.types import PathPattern

if typing.TYPE_CHECKING:
    from typing import Any

    from pydantic import GetCoreSchemaHandler
    from pydantic_core import CoreSchema
    from pydantic_core.core_schema import ValidatorFunctionWrapHandler
    from pydantic_settings import PydanticBaseSettingsSource


class _PathSpecAnnotation:
    """
    Control the type resolution of a path spec.

    This annotation provides a solution to address a type resolution limitation
    in Pydantic 2.10.

    The intended implementation would utilize built-in annotated types for
    ``PathSpec`` without the need for this class:

    .. code-block:: python

       type PathSpec = FilePath | DirectoryPath | PathPattern

    However, Pydantic type resolution mechanism defaults string inputs to
    :py:class:`PathPattern`. This class forces the resolution to the desired
    type.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return pydantic_core.core_schema.no_info_wrap_validator_function(
            cls.validate, handler(source_type)
        )

    @classmethod
    def validate(cls, value: Any, validator: ValidatorFunctionWrapHandler) -> Any:
        if isinstance(value, str):
            try:
                return validator(Path(value))
            except ValueError:
                ...
        return validator(value)


type PathSpec = Annotated[FilePath | DirectoryPath | PathPattern, _PathSpecAnnotation]


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

    exclude: list[PathSpec] = Field(default_factory=list)
    """List of paths or patterns to exclude from the check."""

    include: list[PathSpec] = Field(default=[Path.cwd()])
    """List of paths or patterns to include in the check."""

    follow_symlinks: bool = False
    """Follow symbolic links when checking directories."""

    output_format: Literal["console", "junit"] = "console"
    """Output serialization format."""

    @field_validator("include", "exclude", mode="after")
    @classmethod
    def _reject_dash(cls, values: list[PathSpec]):
        if "-" in values:
            raise ValueError(
                "The value '-' is reserved for stdin. "
                "This option is only available when specified solely via the command line."
            )
        return values


def _find_config(name: str) -> Path | None:
    cwd = Path.cwd()
    for dir_ in itertools.chain([cwd], cwd.parents):
        path = dir_ / name
        if path.is_file():
            return path


settings = Settings()
