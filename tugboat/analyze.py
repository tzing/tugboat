from __future__ import annotations

import logging
import re
import typing

import ruamel.yaml
from ruamel.yaml.comments import CommentedBase, CommentedMap
from ruamel.yaml.error import MarkedYAMLError
from ruamel.yaml.tokens import CommentToken

from tugboat.engine.helpers import get_line_column, get_suppression_codes
from tugboat.engine.mainfest import analyze_manifest

if typing.TYPE_CHECKING:
    from collections.abc import Sequence

    from tugboat.engine import AugmentedDiagnosis

    type CommentTokenSeq = Sequence[CommentToken | str]

logger = logging.getLogger(__name__)

pattern_noqa_all = re.compile(r"#[ ]*noqa(\Z|;)", re.IGNORECASE)
pattern_noqa_line = re.compile(
    r"#[ ]*noqa:[ ]*"  # prefix
    r"("
    r"[a-z]+\d+"  # first code
    r"(?:,[ ]*[A-Z]+[0-9]+)*"  # additional codes, separated by commas
    r")",
    re.IGNORECASE,
)

_yaml_parser = None


def analyze_yaml(manifest: str) -> list[AugmentedDiagnosis]:
    """
    Analyze a YAML manifest and report diagnoses.

    This function internally uses :py:func:`~tugboat.engine.mainfest.analyze_manifest`
    to analyze the manifest.
    The manifest is first parsed into a Python dictionary before being analyzed.

    Parameters
    ----------
    manifest : str
        The YAML manifest to analyze.

    Returns
    -------
    list[Diagnosis]
        The diagnoses reported by the analyzers.
    """
    global _yaml_parser

    if not _yaml_parser:
        _yaml_parser = ruamel.yaml.YAML()

    try:
        documents = _yaml_parser.load_all(manifest)
        documents = list(documents)  # force evaluation
    except MarkedYAMLError as e:
        line = column = 1
        if e.problem_mark:
            line = e.problem_mark.line + 1
            column = e.problem_mark.column + 1

        msg = e.problem or e.context
        if msg and e.context_mark:
            msg += f"\n{e.context_mark}"  # note: context_mark is not a string

        return [
            {
                "line": line,
                "column": column,
                "type": "error",
                "code": "F002",
                "manifest": None,
                "loc": (),
                "summary": "Malformed YAML document",
                "msg": msg,
                "input": None,
                "fix": None,
            }
        ]

    diagnoses = []
    for document in documents:
        if document is None:
            continue

        if not isinstance(document, CommentedBase):
            return [
                {
                    "line": 1,
                    "column": 1,
                    "type": "error",
                    "code": "F002",
                    "manifest": None,
                    "loc": (),
                    "summary": "Malformed YAML document",
                    "msg": "The input is not a YAML document",
                    "input": None,
                    "fix": None,
                }
            ]

        if not isinstance(document, CommentedMap):
            return [
                {
                    "line": document.lc.line + 1,
                    "column": document.lc.col + 1,
                    "type": "error",
                    "code": "F003",
                    "manifest": None,
                    "loc": (),
                    "summary": "Malformed document structure",
                    "msg": "The YAML document should be a mapping",
                    "input": None,
                    "fix": None,
                }
            ]

        for diag in analyze_manifest(document):
            code = diag["code"]
            loc = diag.get("loc", ())
            line, column = get_line_column(document, loc, None)
            manifest_name = _get_manifest_name(document)
            summary = diag.get("summary") or _get_summary(diag.get("msg"))

            line += 1
            column += 1

            if code in get_suppression_codes(document, loc):
                logger.debug(
                    "Suppressed diagnosis %s (%s) in manifest %s at line %d, column %d",
                    code,
                    summary,
                    manifest_name,
                    line,
                    column,
                )
                continue

            diagnoses.append(
                {
                    "line": line,
                    "column": column,
                    "type": diag.get("type", "failure"),
                    "code": code,
                    "manifest": manifest_name,
                    "loc": loc,
                    "summary": summary,
                    "msg": diag["msg"],
                    "input": diag.get("input"),
                    "fix": diag.get("fix"),
                }
            )

    return diagnoses


def _get_summary(msg: str) -> str:
    return (msg or "").strip().splitlines()[0].split(". ")[0]


def _get_manifest_name(manifest: dict) -> str | None:
    metadata = manifest.get("metadata") or {}
    if name := metadata.get("name"):
        return name
    if name := metadata.get("generateName"):
        return name
