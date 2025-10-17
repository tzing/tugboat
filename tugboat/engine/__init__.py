"""
As the engine hums, the boats remembers why it sails.
"""

from __future__ import annotations

__all__ = [
    "DiagnosisModel",
    "FilesystemMetadata",
    "HelmMetadata",
    "ManifestMetadata",
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
from tugboat.engine.types import (
    DiagnosisModel,
    FilesystemMetadata,
    HelmMetadata,
    ManifestMetadata,
)

if typing.TYPE_CHECKING:
    from collections.abc import Iterator
    from os import PathLike
    from typing import Any

logger = logging.getLogger(__name__)
yaml_parser = ruamel.yaml.YAML(typ="rt")


def analyze_yaml_stream(
    stream: str, filepath: str | PathLike[str] | None = None
) -> list[DiagnosisModel]:
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
    list[DiagnosisModel]
        The diagnoses reported by the analyzers.
    """
    digest = hashlib.md5(stream.encode()).hexdigest()
    logger.debug(f"Starting analysis YAML manifest with digest {digest}")

    metadata = None
    if filepath:
        metadata = FilesystemMetadata.model_validate(
            {
                "filepath": str(filepath),
            }
        )

    # parse the YAML stream into documents
    try:
        with io.StringIO(stream) as buf:
            if filepath:
                # set the stream name to the filepath for better error reporting
                # this is a workaround for ruamel.yaml, which does not support setting
                # the name of the stream directly.
                buf.name = str(filepath)
            documents = list(yaml_parser.load_all(buf))  # force evaluation

    except ruamel.yaml.error.MarkedYAMLError as e:
        diagnosis = translate_marked_yaml_error(e)
        diagnosis.extras.file = metadata
        return [diagnosis]

    # analyze each document
    diagnoses: list[DiagnosisModel] = []
    for i, doc in enumerate(documents, 1):
        logger.debug(f"Processing document {i}/{len(documents)} in {digest}")
        if not doc:
            continue

        if isinstance(doc, CommentedMap):
            for diagnosis in analyze_yaml_document(doc):
                diagnosis.extras.file = metadata
                diagnoses.append(diagnosis)

        elif isinstance(doc, CommentedBase):
            type_ = type(doc).__name__
            diagnoses.append(
                DiagnosisModel.model_validate(
                    {
                        "line": doc.lc.line + 1,
                        "column": doc.lc.col + 1,
                        "type": "error",
                        "code": "F003",
                        "loc": (),
                        "summary": "Malformed document structure",
                        "msg": (
                            f"Expected a YAML mapping (key-value pairs) but found a {type_} in document #{i}.\n"
                            "Kubernetes manifests must be structured as objects with properties like 'apiVersion', 'kind', etc."
                        ),
                        "extras": {
                            "file": metadata,
                        },
                    }
                )
            )

        else:
            type_ = type(doc).__name__
            diagnoses.append(
                DiagnosisModel.model_validate(
                    {
                        "line": 1,
                        "column": 1,
                        "type": "error",
                        "code": "F002",
                        "loc": (),
                        "summary": "Malformed input",
                        "msg": f"Expect a YAML mapping (key-value pairs) but found {type(doc).__name__} in document #{i}.",
                        "extras": {
                            "file": metadata,
                        },
                    }
                )
            )

    return diagnoses


def analyze_yaml_document(doc: CommentedMap) -> Iterator[DiagnosisModel]:
    """
    Analyze a single YAML document and report issues.

    This function wraps the :py:func:`analyze_manifest` function and transforms
    the :py:class:`tugboat.types.Diagnosis` objects into :py:class:`DiagnosisModel` objects.
    """
    for diagnosis in analyze_manifest(doc):
        diagnosis = cast("dict[str, Any]", diagnosis)
        diagnosis.setdefault("extras", {})

        if manifest_metadata := diagnosis.get("ctx", {}).get("manifest"):
            diagnosis["extras"]["manifest"] = manifest_metadata

        model = DiagnosisModel.model_validate(diagnosis)

        # TODO exclude diagnoses that are suppressed by settings

        # exclude diagnoses that are suppressed by comments
        if model.code in get_suppression_codes(doc, model.loc):
            manifest_name = "<unnamed>"
            if model.extras.manifest:
                manifest_name = model.extras.manifest.name or manifest_name
            logger.debug(
                "Diagnosis %s (%s) at %s:%s is suppressed by comment",
                model.code,
                model.summary or "<no summary>",
                manifest_name,
                model.loc_path,
            )
            continue

        # update line and column to be 1-based
        line, column = get_line_column(doc, diagnosis["loc"], diagnosis.get("input"))
        model.line = line + 1
        model.column = column + 1

        yield model
