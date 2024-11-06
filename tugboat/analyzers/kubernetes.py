from __future__ import annotations

import re
import typing

if typing.TYPE_CHECKING:
    from tugboat.core import Diagnostic


def check_resource_name(
    name: str, *, length: int = 253, is_generate_name: bool = False
) -> Diagnostic | None:
    """
    Check if the name is valid to be used as a Kubernetes resource name.
    """
    if is_generate_name:
        # although kubernetes automatically truncates the name when it exceeds
        # the length, we want to keep the name as close as possible to the
        # original name to help users identify the resource.
        length -= 5

    if len(name) > length:
        return {
            "type": "failure",
            "code": "M009",
            "loc": (),
            "summary": "Resource name is too long",
            "msg": f"Resource name '{name}' is too long, maximum length is {length}.",
            "input": name,
        }

    if is_generate_name:
        internal_name = name.removesuffix("-")
    else:
        internal_name = name

    pattern = re.compile(r"[a-z0-9]([a-z0-9.-]*[a-z0-9])?")
    if pattern.fullmatch(internal_name):
        return

    diagnostic: Diagnostic = {
        "type": "failure",
        "code": "M010",
        "loc": (),
        "summary": "Invalid resource name",
        "msg": f"""
            Resource name '{name}' is invalid.
            It must consist of lower case alphanumeric characters, '-' or '.', and must start and end with an alphanumeric character.
            """,
        "input": name,
    }

    alternative_name = internal_name.replace("_", "-").lower()
    if pattern.fullmatch(alternative_name):
        if is_generate_name and name.endswith("-"):
            alternative_name += "-"
        diagnostic["fix"] = alternative_name

    return diagnostic
