from __future__ import annotations

import logging
import textwrap
import typing
from typing import Any, Literal, TypedDict

import ruamel.yaml
from pydantic import ValidationError
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import MarkedYAMLError

from tugboat.analyzers.pydantic import translate_pydantic_error
from tugboat.core import get_plugin_manager
from tugboat.schemas import Manifest

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from ruamel.yaml.comments import CommentedBase

    from tugboat.core import Diagnostic

logger = logging.getLogger(__name__)

_yaml_parser = None


class ExtendedDiagnostic(TypedDict):
    """
    A diagnostic reported by the checker.

    This extends the :py:class:`Diagnostic` type by adding extra fields, with
    all members normalized.
    """

    line: int
    """
    Line number of the diagnostic in the source file.
    Note that the line number is cumulative across all documents in the YAML file.
    """

    column: int
    """
    Column number of the diagnostic in the source file.
    """

    type: Literal["error", "failure", "skipped"]
    """The type of diagnostic."""

    code: str
    """The code of the diagnostic."""

    manifest: str | None
    """The manifest name that caused the diagnostic."""

    loc: tuple[str | int, ...]
    """The location of the diagnostic in the manifest."""

    summary: str
    """The summary of the diagnostic."""

    msg: str
    """The detailed message of the diagnostic."""

    input: Any | None
    """The input that caused the diagnostic."""

    fix: str | None
    """The fix to the diagnostic."""


def analyze_yaml(manifest: str) -> list[ExtendedDiagnostic]:
    """
    Analyze a YAML manifest and report diagnostics.

    This function internally uses :py:func:`analyze_raw` to analyze the manifest.
    The manifest is first parsed into a Python dictionary before being analyzed.

    Parameters
    ----------
    manifest : str
        The YAML manifest to analyze.

    Returns
    -------
    list[Diagnostic]
        The diagnostics reported by the analyzers.
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
        return [
            {
                "line": line,
                "column": column,
                "type": "error",
                "code": "F002",
                "manifest": None,
                "loc": (),
                "summary": "Malformed YAML document",
                "msg": e.problem,
                "input": None,
                "fix": None,
            }
        ]

    diagnostics = []
    for document in documents:
        if document is None:
            continue

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

        for diag in analyze_raw(document):
            line, column = _get_line_column(document, diag.get("loc", ()))
            diagnostics.append(
                {
                    "line": line + 1,
                    "column": column + 1,
                    "type": diag.get("type", "failure"),
                    "code": diag["code"],
                    "manifest": _get_manifest_name(document),
                    "loc": diag.get("loc", ()),
                    "summary": diag.get("summary") or _get_summary(diag["msg"]),
                    "msg": diag["msg"],
                    "input": diag.get("input"),
                    "fix": diag.get("fix"),
                }
            )

    return diagnostics


def _get_line_column(node: CommentedBase, loc: Sequence[int | str]) -> tuple[int, int]:
    last_known_pos = node.lc.line, node.lc.col
    for part in loc:
        try:
            pos = node.lc.key(part)
        except KeyError:
            break

        if pos:
            last_known_pos = pos

        try:
            node = node[part]  # type: ignore[reportIndexIssue]
        except (KeyError, IndexError):
            break

        if not hasattr(node, "lc"):
            break

    return last_known_pos


def _get_summary(msg: str) -> str:
    return msg.strip().splitlines()[0].split(". ")[0]


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

    # early exit if the manifest is not a Kubernetes manifest
    if not is_kubernetes_manifest(manifest):
        return [
            {
                "type": "skipped",
                "code": "M001",
                "loc": (),
                "summary": "Not a Kubernetes manifest",
                "msg": "The input does not look like a Kubernetes manifest",
            }
        ]

    # get the manifest name
    name = _get_manifest_name(manifest)
    logger.debug("Analyzing manifest '%s' of kind '%s'", name, manifest.get("kind"))

    # parse the manifest
    try:
        manifest_obj = pm.hook.parse_manifest(manifest=manifest)
    except ValidationError as e:
        return list(map(translate_pydantic_error, e.errors()))
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
        kind = manifest.get("kind")
        return [
            {
                "type": "skipped",
                "code": "M002",
                "loc": ("kind",),
                "msg": f"Manifest of kind '{kind}' is not supported",
                "input": kind,
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

    # examine the manifest
    try:
        diagnostics: Iterable[Diagnostic] = pm.hook.analyze(manifest=manifest_obj)
        diagnostics = list(diagnostics)  # force evaluation
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

    logger.debug("Got %d diagnostics for manifest '%s'", len(diagnostics), name)

    # normalize the diagnostics
    for diagnostic in diagnostics:
        diagnostic.setdefault("code", "UNKNOWN")
        diagnostic["msg"] = textwrap.dedent(diagnostic["msg"]).strip()

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


def is_kubernetes_manifest(d: dict) -> bool:
    """Returns True if the dictionary *looks like* a Kubernetes manifest."""
    return "apiVersion" in d and "kind" in d
