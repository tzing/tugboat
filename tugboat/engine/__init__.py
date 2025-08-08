"""
As the engine hums, the boats remembers why it sails.
"""

from __future__ import annotations

__all__ = [
    "AugmentedDiagnosis",
    "analyze_manifest",
    "analyze_yaml_document",
    "analyze_yaml_stream",
]

import hashlib
import io
import logging
import typing
from typing import cast

import ruamel.yaml
import ruamel.yaml.error
from ruamel.yaml.comments import CommentedBase, CommentedMap

from tugboat.engine.helpers import (
    get_line_column,
    get_suppression_codes,
    translate_marked_yaml_error,
)
from tugboat.engine.mainfest import analyze_manifest
from tugboat.engine.types import AugmentedDiagnosis

if typing.TYPE_CHECKING:
    from collections.abc import Iterator
    from os import PathLike

logger = logging.getLogger(__name__)
yaml_parser = ruamel.yaml.YAML(typ="rt")


def analyze_yaml_stream(
    stream: str, filepath: str | PathLike[str] | None = None
) -> list[AugmentedDiagnosis]:
    """
    Analyze YAML manifest(s) and report issues.

    Parameters
    ----------
    stream : str
        The YAML manifest(s) as a string.
    filepath : PathLike | None
        Path to the manifest file. This is used for error reporting.

    Returns
    -------
    list[AugmentedDiagnosis]
        The diagnoses reported by the analyzers.
    """
    digest = hashlib.md5(stream.encode()).hexdigest()
    logger.debug(f"Starting analysis YAML manifest with digest {digest}")

    try:
        with io.StringIO(stream) as buf:
            if filepath:
                # set the stream name to the filepath for better error reporting
                # this is a workaround for ruamel.yaml, which does not support setting
                # the name of the stream directly.
                buf.name = str(filepath)
            documents = list(yaml_parser.load_all(buf))  # force evaluation

    except ruamel.yaml.error.MarkedYAMLError as e:
        return [translate_marked_yaml_error(e)]

    diagnoses = []
    for i, doc in enumerate(documents, 1):
        logger.debug(f"Processing document {i}/{len(documents)} in {digest}")
        if not doc:
            continue

        if isinstance(doc, CommentedMap):
            diagnoses += analyze_yaml_document(doc)

        elif isinstance(doc, CommentedBase):
            diagnoses.append(
                {
                    "line": doc.lc.line + 1,
                    "column": doc.lc.col + 1,
                    "type": "error",
                    "code": "F003",
                    "manifest": None,
                    "loc": (),
                    "summary": "Malformed document structure",
                    "msg": (
                        f"Expected a YAML mapping (key-value pairs) but found a {type(doc).__name__} in document #{i}.\n"
                        "Kubernetes manifests must be structured as objects with properties like 'apiVersion', 'kind', etc."
                    ),
                    "input": None,
                    "fix": None,
                }
            )

        else:
            diagnoses.append(
                {
                    "line": 1,
                    "column": 1,
                    "type": "error",
                    "code": "F002",
                    "manifest": None,
                    "loc": (),
                    "summary": "Malformed input",
                    "msg": (
                        f"Expect a YAML mapping (key-value pairs) but found {type(doc).__name__} in document #{i}."
                    ),
                    "input": None,
                    "fix": None,
                }
            )

    return diagnoses


def analyze_yaml_document(doc: CommentedMap) -> Iterator[AugmentedDiagnosis]:
    """
    Analyze a single YAML document and report issues.

    This function wraps the :py:func:`analyze_manifest` function and transforms
    the :py:class:`tugboat.types.Diagnosis` objects into :py:class:`AugmentedDiagnosis` objects.
    """
    manifest_metadata = doc.get("metadata", {})
    manifest_name = (
        None
        or manifest_metadata.get("name", None)
        or manifest_metadata.get("generateName", None)
    )

    for diag in analyze_manifest(doc):
        # TODO exclude diagnoses that are suppressed by settings

        # exclude diagnoses that are suppressed by comments
        if diag["code"] in get_suppression_codes(doc, diag["loc"]):
            logger.debug(
                "Diagnosis %s (%s) at %s:%s is suppressed by comment",
                diag["code"],
                diag.get("summary", "<no summary>"),
                manifest_name or "<unnamed manifest>",
                ".".join(map(str, diag["loc"])),
            )
            continue

        # transfrom diagnoses to AugmentedDiagnosis
        line, column = get_line_column(doc, diag["loc"], diag.get("input"))

        yield {
            "line": line + 1,
            "column": column + 1,
            "type": diag.get("type", "failure"),
            "code": diag["code"],
            "manifest": manifest_name,
            "loc": cast("tuple[str | int, ...]", diag["loc"]),
            "summary": diag.get("summary", ""),
            "msg": diag["msg"],
            "input": diag.get("input"),
            "fix": diag.get("fix"),
        }
