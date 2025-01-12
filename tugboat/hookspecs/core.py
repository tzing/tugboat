"""
This module defines the core hook specifications for Tugboat.

These hooks are used to extend the core functionality of Tugboat. Since the
standard Argo Workflows manifest formats are built-in, users may not need to
implement these hooks. However, these hooks are available for users who want to
extend Tugboat to support custom manifest formats or provide custom diagnoses.
"""

from __future__ import annotations

import typing

import pluggy

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.schemas import Manifest
    from tugboat.types import Diagnosis

hookspec = pluggy.HookspecMarker("tugboat")


@hookspec(firstresult=True)
def parse_manifest(manifest: dict) -> Manifest | None:  # type: ignore[reportReturnType]
    """
    Convert a raw manifest into a :py:class:`tugboat.schemas.Manifest` instance
    if the format is recognized by the handler. Returns :py:obj:`None` if the
    format is not recognized.

    During this hook, the framework captures the :py:exc:`pydantic_core.ValidationError`
    raised when parsing the manifest and converts it into a diagnosis. This allows
    the handler to focus on the manifest structure and content, and leave the
    validation to Pydantic and the framework.

    Parameters
    ----------
    manifest : dict
        The manifest to parse.

    Returns
    -------
    Manifest
        The parsed Manifest object if the format is recognized, otherwise :py:obj:`None`.
    """


@hookspec()
def analyze(manifest: Manifest) -> Iterable[Diagnosis]:  # type: ignore[reportReturnType]
    """
    Analyze the manifest and provide diagnoses.

    This is the primary hook invoked during the linting process. The handler
    should examine the manifest and return a list of diagnoses.

    For Argo Workflows manifests, you can implement the hooks in the
    :py:mod:`tugboat.hookspecs.workflow` module. These hooks are wrapped by
    tugboat's built-in handlers, reducing the need to manage the workflow structure.

    Parameters
    ----------
    manifest : Manifest
        The manifest to analyze.

    Returns
    -------
    Iterable[Diagnosis]
        The diagnoses reported by the handler.
    """
