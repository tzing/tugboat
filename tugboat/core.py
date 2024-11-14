from __future__ import annotations

import functools
import typing

import pluggy

if typing.TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any, Literal, NotRequired


hookimpl = pluggy.HookimplMarker("tugboat")


class Diagnosis(typing.TypedDict):
    """A diagnosis reported by the analyzer."""

    type: NotRequired[Literal["error", "failure", "skipped"]]
    """
    The diagnosis type.
    When not provided, it defaults to "failure".
    """

    code: str
    """Diagnosis code."""

    loc: Sequence[str | int]
    """
    The location of the issue occurrence within the manifest, specified in a
    path-like format.

    The first element is the key of the manifest, and the rest are the keys of
    the nested dictionaries.
    """

    summary: NotRequired[str]
    """
    The summary.
    When not provided, the first sentence of the message will be used.
    """

    msg: str
    """
    The detailed message.

    When multiple lines are used in the message, the framework will automatically
    dedent it. This allows the analyzer to use Python multiline strings without
    concern for indentation.
    """

    input: NotRequired[Any]
    """The input that caused the issue."""

    fix: NotRequired[str]
    """The possible fix for the issue."""

    ctx: NotRequired[Any]
    """The additional context."""


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
    import tugboat.analyzers.template
    import tugboat.analyzers.workflow
    import tugboat.analyzers.workflow_template

    pm.register(tugboat.analyzers.template)
    pm.register(tugboat.analyzers.workflow)
    pm.register(tugboat.analyzers.workflow_template)

    return pm
