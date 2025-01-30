from __future__ import annotations

import re
import typing

if typing.TYPE_CHECKING:
    from collections.abc import Iterator

    from tugboat.types import Diagnosis

GENERATED_SUFFIX_LENGTH = 5


def check_resource_name(
    name: str,
    *,
    min_length: int = 1,
    max_length: int = 253,
    is_generate_name: bool = False,
) -> Iterator[Diagnosis]:
    """
    Check if the name is valid to be used as a Kubernetes resource name.

    Yield
    -----
    :ref:`code.m009` for too short or too long name.
    :ref:`code.m010` for invalid characters in the name.

    See also
    --------
    `Object Names and IDs
    <https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names>`_
    """
    if is_generate_name:
        # although kubernetes automatically truncates the name when it exceeds
        # the length, we want to keep the name as close as possible to the
        # original name to help users identify the resource.
        min_length = max(min_length - GENERATED_SUFFIX_LENGTH, 1)
        max_length -= GENERATED_SUFFIX_LENGTH

    if not name:
        yield {
            "type": "failure",
            "code": "M009",
            "loc": (),
            "summary": "Resource name is too short",
            "msg": f"Resource name is empty, minimum length is {min_length}.",
        }
    elif len(name) < min_length:
        yield {
            "type": "failure",
            "code": "M009",
            "loc": (),
            "summary": "Resource name is too short",
            "msg": f"Resource name '{name}' is too short, minimum length is {min_length}.",
            "input": name,
        }

    if len(name) > max_length:
        yield {
            "type": "failure",
            "code": "M009",
            "loc": (),
            "summary": "Resource name is too long",
            "msg": f"Resource name '{name}' is too long, maximum length is {max_length}.",
            "input": name,
        }

    if is_generate_name:
        normalized_name = name.removesuffix("-")
    else:
        normalized_name = name

    pattern = re.compile(r"[a-z0-9]([a-z0-9.-]*[a-z0-9])?")
    if pattern.fullmatch(normalized_name):
        return

    diagnosis: Diagnosis = {
        "type": "failure",
        "code": "M010",
        "loc": (),
        "summary": "Invalid resource name",
        "msg": f"""
            Resource name '{name}' contains invalid characters.
            It must consist of lower case alphanumeric characters, '-' or '.', and must start and end with an alphanumeric character.
            """,
        "input": name,
    }

    alternative_name = normalized_name.replace("_", "-").lower()
    if pattern.fullmatch(alternative_name):
        if is_generate_name and name.endswith("-"):
            alternative_name += "-"
        diagnosis["fix"] = alternative_name

    yield diagnosis
