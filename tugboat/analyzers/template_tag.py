"""
Parser for Argo template tags.

See Also
--------
Workflow Variables
   https://argo-workflows.readthedocs.io/en/latest/variables/
"""

from __future__ import annotations

import functools
import io
import re
import textwrap
import typing
from collections.abc import Sequence

import lark
from pydantic import BaseModel

from tugboat.utils import prepend_loc

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from typing import Any

    from lark import Token
    from lark.exceptions import UnexpectedInput

    from tugboat.references import ReferenceCollection
    from tugboat.types import Diagnosis


def check_template_tags_recursive(
    source: Any,
    references: ReferenceCollection,
    *,
    include: Iterable[str] = (),
    exclude: Iterable[str] = (),
) -> Iterator[Diagnosis]:
    """
    Check each field of the given model for errors in Argo template tags.

    Parameters
    ----------
    source : Any
        The input to check.
    references : ReferenceCollection
        The current active references.
    include : Iterable[str], optional
        The fields to include for checking.
    exclude : Iterable[str], optional
        The fields to exclude from checking.

    Yields
    ------
    Diagnosis
        A diagnosis for each error found.
    """
    if isinstance(source, str):
        yield from check_template_tags(source, references)

    elif isinstance(source, Sequence):
        for idx, item in enumerate(source):
            yield from prepend_loc(
                (idx,),
                check_template_tags_recursive(
                    item, references, include=include, exclude=exclude
                ),
            )

    elif isinstance(source, BaseModel):
        include = set(include)
        exclude = set(exclude)

        for field_name, field_info in type(source).model_fields.items():
            if include and field_name not in include:
                continue
            if field_name in exclude:
                continue

            alias = field_info.alias or field_name
            value = getattr(source, field_name)

            yield from prepend_loc(
                (alias,),
                check_template_tags_recursive(value, references),
            )


@functools.lru_cache(32)
def parse_argo_template_tags(source: str) -> lark.Tree:
    """
    Parse Argo template tags in the given source string.

    Parameters
    ----------
    source : str
        The source string containing Argo template tags.

    Returns
    -------
    lark.Tree
        The parse tree representing the structure of the template tags.
    """
    parser = _argo_template_tag_parser()
    return parser.parse(source)


@functools.cache
def _argo_template_tag_parser():
    return lark.Lark(
        r"""
        %import common.DIGIT
        %import common.LETTER
        %import common.WS

        ?start: (_TEXT | expression_tag | simple_tag)*

        # ignore other text
        _TEXT: /[^{]+/
            | "{" /[^{]/

        # simple template tag
        simple_tag: "{{" WS? REF WS? "}}"
        REF: (LETTER | DIGIT | "_" | "-" | "." | "\"" | "'" | "[" | "]")+

        # expression template tag
        expression_tag: "{{=" _ANY "}}"
        _ANY: /([^}]|}(?!}))+/
        """
    )


def check_template_tags(
    source: str, references: ReferenceCollection
) -> Iterator[Diagnosis]:
    """
    Check the given source string for errors in Argo template tags.

    Parameters
    ----------
    source : str
        The source string containing Argo template tags.
    references : ReferenceCollection
        The current active references.

    Yields
    ------
    Diagnosis
        A diagnosis for each error found.
    """
    try:
        tree = parse_argo_template_tags(source)
    except lark.UnexpectedInput as e:
        yield transform_lark_error(source, e)
        return

    # analyze simple tags
    for tag in tree.find_data("simple_tag"):
        (ref_repr,) = tag.find_token("REF")
        ref_repr = typing.cast("Token", ref_repr)
        if diagnosis := _check_simple_tag_reference(ref_repr, references):
            yield diagnosis


def transform_lark_error(source: str, e: UnexpectedInput) -> Diagnosis:
    with io.StringIO() as buf:
        buf.write("The field contains a syntax error for Argo template tags.")
        buf.write("\n\n")
        buf.write("The parser reported the errors near:\n\n")
        buf.write(textwrap.indent(e.get_context(source), "  "))

        match type(e):
            case lark.UnexpectedCharacters:
                buf.write(
                    "\n"
                    "This error is usually caused by invalid characters in the template tag.\n"
                    "Please ensure that the template tags are correctly formatted."
                )
            case lark.UnexpectedEOF:
                buf.write(
                    "\n"
                    "This error is usually caused by an incomplete template tag.\n"
                    "Please ensure that all template tags are properly closed."
                )

        message = buf.getvalue()

    return {
        "type": "error",
        "code": "VAR101",
        "loc": (),
        "summary": "Syntax error",
        "msg": message,
    }


def _check_simple_tag_reference(
    ref_repr: str, references: ReferenceCollection
) -> Diagnosis | None:
    # early exit if the reference is known
    ref = tuple(ref_repr.split("."))
    if ref in references:
        return

    # case: user mistakenly use the expression tag format
    if parts := split_expr_membership(ref_repr):
        if parts in references:
            # case: the reference exists, but the format is wrong
            # this is common when the reference is built by coding agents
            fix = ".".join(parts)
            return {
                "code": "VAR102",
                "loc": (),
                "summary": "Incorrect template tag format",
                "msg": (
                    f"""
                    The reference '{ref_repr}' mistakes the expression tag format in a simple tag.
                    Use the simple tag format instead, or convert it to an expression tag ({{{{= ... }}}}) if needed.
                    """
                ),
                "input": ref_repr,
                "fix": fix,
            }

        else:
            # case: the reference does not exist
            # leave it to the unknown variable checker
            ref = parts
            ref_repr = ".".join(parts)

    if any(sym in ref_repr for sym in "'\"[]"):
        # well-formed bracket notations should have been handled by split_expr_membership above
        # reaching here means the reference contains unexpected characters
        return {
            "code": "VAR101",
            "loc": (),
            "summary": "Syntax error",
            "msg": (
                f"""
                The input '{ref_repr}' contains invalid characters for simple template tag.

                Simple tags only support dot notation (e.g., `inputs.parameters.name`).
                For complex expressions, use expression tags instead: `{{{{= ... }}}}`.
                """
            ),
            "input": ref_repr,
        }

    # case: the reference doesn't look like an Argo variable
    if is_variable(ref_repr) and not has_simple_variable(references):
        return {
            "type": "warning",
            "code": "VAR202",
            "loc": (),
            "summary": "Not a Argo workflow variable reference",
            "msg": (
                f"""
                The used reference '{ref_repr}' is invalid for Argo workflow variables.

                If this `{{{{ }}}}` tag is intended for other templating engines (e.g., Jinja),
                you can ignore this warning, or suppress it by adding a:

                  # noqa: VAR202; non-Argo variable reference

                comment on the field or model using this variable.
                """
            ),
            "input": ref_repr,
        }

    # case: unknown variable
    metadata = {
        "found": ref,
        "found:str": ref_repr,
    }

    if closest := references.find_closest(ref):
        metadata["closest"] = closest
        metadata["closest:str"] = ".".join(closest)

    return {
        "code": "VAR201",
        "loc": (),
        "summary": "Unknown Argo workflow variable reference",
        "msg": (
            f"The reference '{ref_repr}' is not recognized as a valid Argo workflow variable under the current context."
        ),
        "input": ref_repr,
        "fix": metadata.get("closest:str"),
        "ctx": {"reference": metadata},
    }


def split_expr_membership(source: str) -> tuple[str, ...]:
    """
    Split an expr lang membership string into its components.

    Parameters
    ----------
    source : str
        The expression membership string.

    Returns
    -------
    tuple[str, ...]
        The components of the expression membership.
    """
    # extract first part
    match_ = re.match(r"[a-zA-Z_]\w*", source)
    if not match_:
        return ()

    parts = [match_.group(0)]

    regex_parts = re.compile(
        r"""
        \.([a-zA-Z_]\w*)    # dot notation
        |\['([\w-]+)'\]     # single-quoted bracket notation
        |\[\"([\w-]+)\"\]   # double-quoted bracket notation
        """,
        re.VERBOSE,
    )

    while match_.end() < len(source):
        match_ = regex_parts.match(source, match_.end())
        if not match_:
            return ()

        parts += filter(None, match_.groups())

    return tuple(parts)


def is_variable(s: str) -> bool:
    return re.fullmatch(r"[_a-zA-Z][_a-zA-Z0-9]*", s) is not None


def has_simple_variable(references: ReferenceCollection) -> bool:
    for ref in references:
        if len(ref) == 1:
            return True
    return False
