from __future__ import annotations

import itertools
import logging
import textwrap
import typing

import ruamel.yaml
from pydantic import ValidationError
from ruamel.yaml.comments import CommentedBase, CommentedMap
from ruamel.yaml.error import MarkedYAMLError

from tugboat.analyzers import translate_pydantic_error
from tugboat.core import get_plugin_manager
from tugboat.schemas import Manifest

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

    from ruamel.yaml.tokens import CommentToken

    from tugboat.types import AugmentedDiagnosis, Diagnosis

    type CommentTokenSeq = Sequence[CommentToken]

logger = logging.getLogger(__name__)

_yaml_parser = None


def analyze_yaml(manifest: str) -> list[AugmentedDiagnosis]:
    """
    Analyze a YAML manifest and report diagnoses.

    This function internally uses :py:func:`analyze_raw` to analyze the manifest.
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

        for diag in analyze_raw(document):
            line, column = _get_line_column(document, diag.get("loc", ()))
            diagnoses.append(
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

    return diagnoses


def _get_line_column(node: CommentedBase, loc: Sequence[int | str]) -> tuple[int, int]:
    last_known_pos = node.lc.line, node.lc.col
    for part in loc:
        try:
            if pos := node.lc.key(part):
                last_known_pos = pos
        except KeyError:
            break

        try:
            node = node[part]  # type: ignore[reportIndexIssue]
        except (KeyError, IndexError):
            break

        if not isinstance(node, CommentedBase):
            break

    return last_known_pos


def _find_related_comments(
    node: CommentedBase, loc: Sequence[int | str]
) -> Iterator[str]:
    #  idx:   1     2     3
    # node: foo > bar > baz
    #             └── `node.ca.items.get` returns `baz`'s comment
    for idx, part in enumerate(loc, 1):
        if ca := node.ca.items.get(part):
            pre, post = _extract_comment_tokens(ca)
            # for parent nodes, return the leading comments
            if pre:
                yield _extract_comment_text(pre)
            # for the last node, return the trailing comments
            if idx >= len(loc) - 1 and post:
                yield _extract_comment_text(post)

        try:
            node = node[part]  # type: ignore[reportIndexIssue]
        except (KeyError, IndexError):
            break

        if not isinstance(node, CommentedBase):
            break


def _extract_comment_tokens(comment_items) -> Iterator[CommentTokenSeq]:
    if len(comment_items) == 2:  # node is a list
        pre, post = comment_items
    elif len(comment_items) == 4:  # node is a mapping
        _, _, post, pre = comment_items
    else:
        raise RuntimeError(f"Unexpected comment item: {comment_items:!r}")

    pre: list[CommentToken] | None
    post: CommentToken | None

    yield pre or ()
    yield [post] if post else ()


def _extract_comment_text(seq: CommentTokenSeq) -> str:
    return "".join(token.value for token in seq)


def _get_summary(msg: str) -> str:
    return msg.strip().splitlines()[0].split(". ")[0]


def analyze_raw(manifest: dict) -> list[Diagnosis]:
    """
    Analyze a raw manifest and report diagnoses.

    This function underlyingly uses the plugin manager to run the analyzers
    registered with the system. The diagnoses are collected and returned
    as a list of Diagnosis objects.

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
        logger.debug(
            "Manifest '%s' (kind %s) is not supported", name, manifest.get("kind")
        )
        return []

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
        analyzers_diagnoses: Iterable[Iterator[Diagnosis]]
        analyzers_diagnoses = pm.hook.analyze(manifest=manifest_obj)
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

    # normalize the diagnoses
    for diagnosis in diagnoses:
        diagnosis.setdefault("code", "UNKNOWN")
        diagnosis["msg"] = textwrap.dedent(diagnosis["msg"]).strip()

    # sort the diagnoses
    def _sort_key(diagnosis: Diagnosis) -> tuple:
        return (
            # 1. position of the occurrence
            tuple(diagnosis.get("loc", [])),
            # 2. diagnosis code
            diagnosis.get("code") or "",
        )

    diagnoses = sorted(diagnoses, key=_sort_key)

    return diagnoses


def _get_manifest_name(manifest: dict) -> str | None:
    metadata = manifest.get("metadata") or {}
    if name := metadata.get("name"):
        return name
    if name := metadata.get("generateName"):
        return name


def is_kubernetes_manifest(d: dict) -> bool:
    """Returns True if the dictionary *looks like* a Kubernetes manifest."""
    return "apiVersion" in d and "kind" in d
