from __future__ import annotations

import functools
import typing

import pluggy

if typing.TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any, Literal, NotRequired


hookimpl = pluggy.HookimplMarker("tugboat")


class Diagnostic(typing.TypedDict):
    """
    A diagnostic reported by the checker.
    """

    type: NotRequired[Literal["error", "failure", "skipped"]]
    """
    The type of diagnostic.
    When not provided, it defaults to "failure".
    """

    code: str
    """The code of the diagnostic."""

    loc: Sequence[str | int]
    """
    The location of the diagnostic in the manifest.
    The first element is the key of the manifest, and the rest are the keys of
    the nested dictionaries.
    """

    summary: NotRequired[str]
    """
    The summary of the diagnostic.
    When not provided, the first sentence of the message will be used.
    """

    msg: str
    """
    The detailed message of the diagnostic.
    When multiple lines are used in the message, the framework will automatically dedent it.
    This allows the analyzer to use Python multiline strings without concern for indentation.
    """

    input: NotRequired[Any]
    """The input that caused the diagnostic."""

    fix: NotRequired[str]
    """The fix to the diagnostic."""

    ctx: NotRequired[Any]
    """The additional context of the diagnostic."""


@functools.lru_cache(1)
def get_plugin_manager() -> pluggy.PluginManager:
    pm = pluggy.PluginManager("tugboat")
    pm.load_setuptools_entrypoints("tugboat")

    # hook specs
    import tugboat.hookspecs.core
    import tugboat.hookspecs.workflow

    pm.add_hookspecs(tugboat.hookspecs.core)
    pm.add_hookspecs(tugboat.hookspecs.workflow)

    # hook implementations
    import tugboat.analyzers.workflow
    import tugboat.analyzers.workflow_template

    pm.register(tugboat.analyzers.workflow)
    pm.register(tugboat.analyzers.workflow_template)

    return pm
