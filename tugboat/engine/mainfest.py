from __future__ import annotations

import hashlib
import itertools
import logging
import textwrap
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

    # get the manifest name
    kind, name = get_manifest_kind_and_name(manifest)
    logger.debug("Starting analysis of manifest '%s' (Kind %s)", name, kind)

    # parse the manifest
    try:
        manifest_obj = pm.hook.parse_manifest(manifest=manifest)
    except ValidationError as e:
        return bulk_translate_pydantic_errors(e.errors())
    except Exception as e:
        logger.exception("Error during execution of parse_manifest hook")
        return [
            {
                "type": "error",
                "code": "F001",
                "loc": (),
                "summary": "Internal error while analyzing manifest",
                "msg": f"An error occurred while parsing the manifest: {e}",
            }
        ]

    logger.debug("Parsed manifest '%s' as %s object", name, type(manifest_obj))

    if not manifest_obj:
        return [
            {
                "type": "warning",
                "code": "M002",
                "loc": (),
                "summary": "Unsupported manifest kind",
                "msg": f"Manifest kind {kind} is not supported",
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
            }
        ]

    logger.debug("Got %d diagnoses for manifest '%s'", len(diagnoses), name)

    # sort the diagnoses
    def _sort_key(diagnosis: Diagnosis) -> tuple:
        return (
            # 1. position of the occurrence
            diagnosis["loc"],
            # 2. diagnosis code
            diagnosis["code"],
        )

    diagnoses = map(normalize_diagnosis, diagnoses)
    diagnoses = sorted(diagnoses, key=_sort_key)

    return diagnoses


def is_kubernetes_manifest(d: dict) -> bool:
    """Returns True if the dictionary *looks like* a Kubernetes manifest."""
    return "apiVersion" in d and "kind" in d


def get_manifest_kind_and_name(manifest: dict) -> tuple[str, str]:
    """Get the kind and name of the manifest."""
    # extract group
    if api_version := manifest["apiVersion"]:
        group, *_ = api_version.split("/", 1)
    else:
        group = "unknown"

    # extract kind
    kind = manifest["kind"] or "Unknown"

    # extract name
    metadata = manifest.get("metadata") or {}
    name = metadata.get("name") or metadata.get("generateName") or "<unknown>"

    return f"{group}/{kind}", name


def normalize_diagnosis(diagnosis: Diagnosis) -> Diagnosis:
    # loc
    loc = diagnosis.setdefault("loc", ())
    if not isinstance(loc, tuple):
        diagnosis["loc"] = tuple(loc)

    # msg
    msg = diagnosis.get("msg") or ""
    msg = textwrap.dedent(msg).strip()
    diagnosis["msg"] = msg

    # summary
    summary = diagnosis.get("summary")
    if not summary:
        if msg:
            first_line, *_ = msg.splitlines()
            summary, *_ = first_line.split(". ")
            diagnosis["summary"] = summary.strip()
        else:
            diagnosis["summary"] = ""

    # code
    if diagnosis.get("code") is None:
        digest = hashlib.md5(msg.encode()).hexdigest()
        diagnosis["code"] = f"F-{digest[:6].upper()}"
        logger.warning("Missing code for diagnosis %s", diagnosis["code"])
        logger.debug("Diagnosis: %s", diagnosis)

    return diagnosis
