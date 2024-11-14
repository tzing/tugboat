from __future__ import annotations

import itertools
import logging
import textwrap
import typing
from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypedDict

import ruamel.yaml
from pydantic import ValidationError
from rapidfuzz.process import extractOne
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import MarkedYAMLError

from tugboat.core import get_plugin_manager
from tugboat.schemas import Manifest
from tugboat.utils import get_context_name

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from typing import Any

    from pydantic_core import ErrorDetails
    from ruamel.yaml.comments import CommentedBase

    from tugboat.core import Diagnosis

logger = logging.getLogger(__name__)

_yaml_parser = None


class AugmentedDiagnosis(TypedDict):
    """
    The augmented diagnosis reported by the analyzer.

    This type extends the :py:class:`Diagnosis` and adds additional fields
    to provide more context about the diagnosis.
    """

    line: int
    """
    Line number of the issue occurrence in the source file.
    Note that the line number is cumulative across all documents in the YAML file.
    """

    column: int
    """
    Column number of the issue occurrence in the source file.
    """

    type: Literal["error", "failure", "skipped"]
    """The type that describes the severity."""

    code: str
    """Diagnosis code."""

    manifest: str | None
    """The manifest name where the issue occurred."""

    loc: tuple[str | int, ...]
    """
    The location of the issue occurrence within the manifest, specified in a
    path-like format.
    """

    summary: str
    """The summary."""

    msg: str
    """The detailed message."""

    input: Any | None
    """The input that caused the issue."""

    fix: str | None
    """The possible fix for the issue."""


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

    diagnoses = []
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
    metadata = manifest.get("metadata", {})
    if name := metadata.get("name"):
        return name
    if name := metadata.get("generateName"):
        return name


def is_kubernetes_manifest(d: dict) -> bool:
    """Returns True if the dictionary *looks like* a Kubernetes manifest."""
    return "apiVersion" in d and "kind" in d


def translate_pydantic_error(error: ErrorDetails) -> Diagnosis:
    """Translate a Pydantic error to a diagnosis object."""
    field = error["loc"][-1]

    match error["type"]:
        case "bool_parsing" | "bool_type":
            input_type = get_type_name(error["input"])
            return {
                "type": "failure",
                "code": "M007",
                "loc": error["loc"],
                "summary": "Input should be a valid boolean",
                "msg": f"""
                    Field '{field}' should be a valid boolean, got {input_type}.
                    Try using 'true' or 'false' without quotes.
                    """,
                "input": error["input"],
            }

        case "enum" | "literal_error":
            expected_literal = error.get("ctx", {}).get("expected", "")
            expected = _extract_expects(expected_literal)

            input_ = error["input"]
            fix, _, _ = extractOne(error["input"], expected)

            return {
                "type": "failure",
                "code": "M008",
                "loc": error["loc"],
                "summary": error["msg"],
                "msg": f"""
                    Input '{input_}' is not a valid value for field '{field}'.
                    Expected {expected_literal}.
                    """,
                "input": error["input"],
                "fix": fix,
            }

        case "extra_forbidden":
            *parents, _ = error["loc"]
            return {
                "type": "failure",
                "code": "M005",
                "loc": error["loc"],
                "summary": "Found redundant field",
                "msg": f"Field '{field}' is not valid within {get_context_name(parents)}.",
                "input": field,
            }

        case "int_parsing" | "int_type":
            input_type = get_type_name(error["input"])
            return {
                "type": "failure",
                "code": "M007",
                "loc": error["loc"],
                "summary": "Input should be a valid integer",
                "msg": f"Field '{field}' should be a valid integer, got {input_type}.",
                "input": error["input"],
            }

        case "missing":
            return {
                "type": "failure",
                "code": "M004",
                "loc": error["loc"],
                "summary": "Missing required field",
                "msg": f"Field '{field}' is required but missing",
            }

        case "string_type":
            input_type = get_type_name(error["input"])
            msg = [f"Field '{field}' should be a valid string, got {input_type}."]
            msg += _guess_string_problems(error["input"])
            return {
                "type": "failure",
                "code": "M007",
                "loc": error["loc"],
                "summary": "Input should be a valid string",
                "msg": "\n".join(msg),
                "input": error["input"],
            }

    return {
        "type": "failure",
        "code": "M003",
        "loc": error["loc"],
        "msg": error["msg"],
        "input": error["input"],
        "ctx": {"pydantic_error": error},
    }


def _extract_expects(literal: str) -> Iterator[str]:
    """
    Extract the expected values from the error message.

    The expected values are like:

    .. code-block:: none

       "hello'", 'world' or 'hola'
    """
    idx = 0
    while idx < len(literal):
        if literal[idx] == "'":
            idx_end = literal.find("'", idx + 1)
            yield literal[idx + 1 : idx_end]
            idx = idx_end + 1

        elif literal[idx] == '"':
            idx_end = literal.find('"', idx + 1)
            yield literal[idx + 1 : idx_end]
            idx = idx_end + 1

        else:
            idx += 1


def _guess_string_problems(value: Any):
    """
    Guess the problems with the string input, return a list of suggestions.

    Ref: https://ruudvanasseldonk.com/2023/01/11/the-yaml-document-from-hell
    """
    # the Norway problem
    if isinstance(value, bool):
        if value is True:
            yield "Note that these inputs will be interpreted as boolean true: 'True', 'Yes', 'On', 'Y'."
        else:
            yield "Note that these inputs will be interpreted as boolean false: 'False', 'No', 'Off', 'N'."

    # sexagesimal
    if isinstance(value, int) and 60 < value <= 3600:
        sexagesimal = _to_sexagesimal(value)
        yield (
            f"Sequence of number separated by colons (e.g. {sexagesimal}) "
            "will be interpreted as sexagesimal."
        )

    # general suggestion
    yield "Try using quotes for strings to fix this issue."


def _to_sexagesimal(value: int) -> str:
    """Convert an integer to a sexagesimal string."""
    if value < 0:
        sign = "-"
        value = -value
    else:
        sign = ""

    digits = []
    while value:
        digits.append(value % 60)
        value //= 60

    return sign + ":".join(str(d) for d in reversed(digits))


def get_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, str):
        return "string"
    if isinstance(value, float):
        return "floating point number"
    if isinstance(value, Mapping):
        return "mapping"
    if isinstance(value, Sequence):
        return "sequence"
    return type(value).__name__
