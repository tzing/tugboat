from __future__ import annotations

import itertools
import logging
import re
import textwrap
import typing

import ruamel.yaml
from pydantic import ValidationError
from ruamel.yaml.comments import CommentedBase, CommentedMap
from ruamel.yaml.error import MarkedYAMLError
from ruamel.yaml.tokens import CommentToken

from tugboat.core import get_plugin_manager
from tugboat.schemas import Manifest
from tugboat.utils import bulk_translate_pydantic_errors

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

    from tugboat.types import AugmentedDiagnosis, Diagnosis

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
            code = diag["code"]
            loc = diag.get("loc", ())
            line, column = _get_line_column(document, loc)
            manifest_name = _get_manifest_name(document)
            summary = diag.get("summary") or _get_summary(diag.get("msg"))

            line += 1
            column += 1

            if _should_ignore_code(code, _find_related_comments(document, loc)):
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
    for part in loc:
        if ca := node.ca.items.get(part):
            pre, post = _extract_comment_tokens(ca)
            if pre:
                yield _extract_comment_text(pre)
            if post:
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

    pre: list[CommentToken | str] | None
    post: CommentToken | None

    yield pre or ()
    yield [post] if post else ()


def _extract_comment_text(seq: CommentTokenSeq) -> str:
    def _normalize(token: CommentToken | str) -> str:
        if isinstance(token, CommentToken):
            return token.value
        return str(token)

    return "".join(map(_normalize, seq)).strip()


def _should_ignore_code(code: str, comments: Iterable[str]) -> bool:
    """Returns True if the code should be suppressed."""
    for ignore_code in _extract_noqa_codes(comments):
        if ignore_code == "ALL":
            return True
        if ignore_code == code:
            return True
    return False


def _extract_noqa_codes(comments: Iterable[str]) -> Iterable[str]:
    """Extracts the noqa codes from the comments."""
    for comment in comments:
        if pattern_noqa_all.match(comment):
            yield "ALL"
            return  # pragma: no cover; the caller may breaks the loop

        if m := pattern_noqa_line.match(comment):
            for code in m.group(1).split(","):
                yield code.strip().upper()


def _get_summary(msg: str) -> str:
    return (msg or "").strip().splitlines()[0].split(". ")[0]


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
    kind = _get_manifest_kind(manifest)
    name = _get_manifest_name(manifest)
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
        logger.debug("Kind %s is not supported. Skipping manigest %s.", kind, name)
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
            tuple(diagnosis.get("loc", [])),
            # 2. diagnosis code
            diagnosis.get("code") or "",
        )

    diagnoses = map(_sanitize_diagnosis, diagnoses)
    diagnoses = sorted(diagnoses, key=_sort_key)

    return diagnoses


def _get_manifest_name(manifest: dict) -> str | None:
    metadata = manifest.get("metadata") or {}
    if name := metadata.get("name"):
        return name
    if name := metadata.get("generateName"):
        return name


def _get_manifest_kind(manifest: dict) -> str | None:
    if api_version := manifest.get("apiVersion"):
        group, *_ = api_version.split("/", 1)
    else:
        group = "unknown"
    kind = manifest.get("kind") or "Unknown"
    return f"{group}/{kind}"


def _sanitize_diagnosis(diagnosis: Diagnosis) -> Diagnosis:
    diagnosis.setdefault("code", "UNKNOWN")
    diagnosis["msg"] = textwrap.dedent(diagnosis["msg"]).strip()
    return diagnosis


def is_kubernetes_manifest(d: dict) -> bool:
    """Returns True if the dictionary *looks like* a Kubernetes manifest."""
    return "apiVersion" in d and "kind" in d
