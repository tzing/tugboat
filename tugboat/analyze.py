from __future__ import annotations

import logging
import typing

from pydantic import ValidationError

from tugboat.core import get_plugin_manager
from tugboat.schemas import Manifest

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from tugboat.core import Diagnostic

logger = logging.getLogger(__name__)


def analyze_raw(manifest: dict) -> list[Diagnostic]:
    """
    Analyze a raw manifest and report diagnostics.

    This function underlyingly uses the plugin manager to run the analyzers
    registered with the system. The diagnostics are collected and returned
    as a list of Diagnostic objects.

    Parameters
    ----------
    manifest : dict
        The manifest to analyze.

    Returns
    -------
    list[Diagnostic]
        The diagnostics reported by the analyzers.
    """
    pm = get_plugin_manager()

    name = _get_manifest_name(manifest)
    logger.debug("Analyzing manifest '%s' of kind '%s'", name, manifest.get("kind"))

    # parse the manifest
    try:
        manifest_obj = pm.hook.parse_manifest(manifest=manifest)
    except ValidationError as e:
        output = []
        for error in e.errors():
            output.append(
                {
                    "type": "failure",
                    "code": "M001",
                    "loc": error["loc"],
                    "msg": error["msg"],
                    "input": error["input"],
                }
            )
        return output
    except Exception as e:
        logger.exception("Error during execution of parse_manifest hook")
        return [
            {
                "type": "error",
                "code": "E001",
                "loc": (),
                "summary": "Internal error while analyzing manifest",
                "msg": f"An error occurred while parsing the manifest: {e}",
            }
        ]

    logger.debug("Parsed manifest '%s' as %s object", name, type(manifest_obj))

    if not manifest_obj:
        kind = manifest.get("kind")
        return [
            {
                "type": "skipped",
                "code": "M002",
                "loc": (),
                "msg": f"Manifest of kind '{kind}' is not supported",
            }
        ]

    if not isinstance(manifest_obj, Manifest):
        return [
            {
                "type": "error",
                "code": "E001",
                "loc": (),
                "summary": "Internal error while analyzing manifest",
                "msg": f"Expected a Manifest object, got {type(manifest_obj)}",
            }
        ]

    # examine the manifest
    try:
        diagnostics: Iterable[Diagnostic] = pm.hook.analyze(manifest=manifest_obj)
        diagnostics = list(diagnostics)  # force evaluation
    except Exception as e:
        logger.exception("Error during execution of analyze hook")
        return [
            {
                "type": "error",
                "code": "E001",
                "loc": (),
                "summary": "Internal error while analyzing manifest",
                "msg": f"An error occurred while analyzing the manifest: {e}",
            }
        ]

    logger.debug("Got %d diagnostics for manifest '%s'", len(diagnostics), name)

    # sort the diagnostics
    def _sort_key(diagnostic: Diagnostic) -> tuple:
        return (
            # 1. position of the occurrence
            tuple(diagnostic.get("loc", [])),
            # 2. diagnostic code
            diagnostic.get("code") or "",
        )

    diagnostics = sorted(diagnostics, key=_sort_key)

    return diagnostics


def _get_manifest_name(manifest: dict) -> str | None:
    metadata = manifest.get("metadata", {})
    if name := metadata.get("name"):
        return name
    if name := metadata.get("generateName"):
        return name
