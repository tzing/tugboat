from __future__ import annotations

import itertools
import logging
import typing

from pydantic import ValidationError

from tugboat.core import get_plugin_manager
from tugboat.schemas import Manifest
from tugboat.utils import bulk_translate_pydantic_errors

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from tugboat.types import Diagnosis


logger = logging.getLogger(__name__)


def analyze_manifest(manifest: dict) -> list[Diagnosis]:
    """
    Analyze the manifest and return a list of diagnoses.

    This function uses the plugin system to analyze the manifest. The diagnoses
    are collected and returned as a list.

    Parameters
    ----------
    manifest : dict
        The manifest to analyze.

    Returns
    -------
    list[Diagnosis]
        The diagnoses reported by the analyzers.
    """
    pm = get_plugin_manager()

    # early exit if the manifest is not a Kubernetes manifest
    if not is_kubernetes_manifest(manifest):
        return [
            {
                "type": "warning",
                "code": "M001",
                "loc": (),
                "summary": "Not a Kubernetes manifest",
                "msg": "The input does not look like a Kubernetes manifest",
            }
        ]

    # get manifest metadata
    metadata = get_manifest_metadata(manifest)
    logger.debug(
        "Starting analysis of manifest '%s' (Kind %s)",
        metadata.get("name", "<unknown>"),
        metadata["kind"],
    )

    # parse the manifest
    try:
        manifest_obj = pm.hook.parse_manifest(manifest=manifest)
    except ValidationError as e:
        diagnoses = bulk_translate_pydantic_errors(e.errors())
        for diagnosis in diagnoses:
            context = diagnosis.setdefault("ctx", {})
            context["manifest"] = metadata
        return diagnoses
    except Exception as e:
        logger.exception("Error during execution of parse_manifest hook")
        return [
            {
                "type": "error",
                "code": "F001",
                "loc": (),
                "summary": "Internal error while analyzing manifest",
                "msg": f"An error occurred while parsing the manifest: {e}",
                "ctx": {"manifest": metadata},
            }
        ]

    logger.debug(
        "Parsed manifest '%s' as %s object",
        metadata.get("name", "<unknown>"),
        type(manifest_obj),
    )

    if not manifest_obj:
        return [
            {
                "type": "warning",
                "code": "M002",
                "loc": (),
                "summary": "Unsupported manifest kind",
                "msg": f"Manifest kind {metadata['kind']} is not supported",
                "ctx": {"manifest": metadata},
            }
        ]

    if not isinstance(manifest_obj, Manifest):
        return [
            {
                "type": "error",
                "code": "F001",
                "loc": (),
                "summary": "Internal error while analyzing manifest",
                "msg": f"Expected a Manifest object, got {type(manifest_obj)}",
                "ctx": {"manifest": metadata},
            }
        ]

    # analyze the manifest
    analyzers_diagnoses: Iterable[Iterator[Diagnosis]]
    analyzers_diagnoses = pm.hook.analyze(manifest=manifest_obj)

    try:  # force evaluation
        diagnoses = list(itertools.chain.from_iterable(analyzers_diagnoses))
    except Exception as e:
        logger.exception("Error during execution of analyze hook")
        return [
            {
                "type": "error",
                "code": "F001",
                "loc": (),
                "summary": "Internal error while analyzing manifest",
                "msg": f"An error occurred while analyzing the manifest: {e}",
                "ctx": {"manifest": metadata},
            }
        ]

    logger.debug(
        "Got %d diagnoses for manifest '%s'",
        len(diagnoses),
        metadata.get("name", "<unknown>"),
    )

    # sort the diagnoses
    def _sort_key(diagnosis: Diagnosis) -> tuple:
        return (
            # 1. position of the occurrence
            diagnosis["loc"],
            # 2. diagnosis code
            diagnosis["code"],
        )

    diagnoses = sorted(diagnoses, key=_sort_key)

    # add manifest info to each diagnosis
    for diagnosis in diagnoses:
        context = diagnosis.setdefault("ctx", {})
        context["manifest"] = metadata

    return diagnoses


def is_kubernetes_manifest(d: dict) -> bool:
    """Returns True if the dictionary *looks like* a Kubernetes manifest."""
    return isinstance(d.get("apiVersion"), str) and isinstance(d.get("kind"), str)


def get_manifest_metadata(manifest: dict) -> dict[str, str]:
    """Safely extract metadata from the manifest."""
    # full qualified kind
    if api_version := manifest.get("apiVersion"):
        group, *_ = api_version.split("/", 1)
    else:
        group = "unknown"

    kind = manifest.get("kind") or "Unknown"

    output = {
        "kind": f"{group}/{kind}",
    }

    # name / namespace
    if metadata := manifest.get("metadata"):
        if name := metadata.get("name") or metadata.get("generateName"):
            output["name"] = name
        if namespace := metadata.get("namespace"):
            output["namespace"] = namespace

    return output
