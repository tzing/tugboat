from __future__ import annotations

import typing

import pluggy

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.core import Diagnosis
    from tugboat.schemas import Manifest

hookspec = pluggy.HookspecMarker("tugboat")


@hookspec(firstresult=True)
def parse_manifest(manifest: dict) -> Manifest | None:  # type: ignore[reportReturnType]
    """
    Convert a raw manifest into a Manifest instance if the format is recognized
    by the handler. Return :py:obj:`None` if the format is not recognized.

    Parameters
    ----------
    manifest : dict
        The manifest to parse.

    Returns
    -------
    WorkflowTemplate
        The parsed Manifest object.
    """


@hookspec()
def analyze(manifest: Manifest) -> Iterable[Diagnosis]:  # type: ignore[reportReturnType]
    """
    Analyze the manifest and provide diagnoses.

    Parameters
    ----------
    manifest : Manifest
        The manifest to analyze.

    Returns
    -------
    Iterable[Diagnosis]
        The diagnoses reported by the handler.
    """
