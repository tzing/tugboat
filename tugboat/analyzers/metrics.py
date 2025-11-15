from __future__ import annotations

import re
import typing

from tugboat.constraints import mutually_exclusive, require_all
from tugboat.utils import check_model_fields_references

if typing.TYPE_CHECKING:
    from collections.abc import Iterator

    from tugboat.references import Context
    from tugboat.schemas.metrics import Prometheus
    from tugboat.types import Diagnosis


def check_prometheus(prometheus: Prometheus, context: Context) -> Iterator[Diagnosis]:
    """
    Check :py:class:``tugboat.schemas.metrics.Prometheus`` for errors.
    """

    yield from require_all(
        model=prometheus,
        fields=["name", "help"],
    )
    yield from mutually_exclusive(
        prometheus,
        fields=["counter", "gauge", "histogram"],
        require_one=True,
    )
    yield from check_model_fields_references(
        model=prometheus,
        references=context.parameters,
    )

    if prometheus.name:
        if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", prometheus.name):
            yield {
                "type": "failure",
                "code": "internal:invalid-metric-name",
                "loc": ("name",),
                "summary": "Invalid metric name",
                "msg": f"""
                    Metric name '{prometheus.name}' is invalid.
                    Argo Workflows metric names must start with an alphabetic character and can only include alphanumeric characters and underscores (_).
                    """,
                "input": prometheus.name,
            }

        if len(prometheus.name) > 255:
            yield {
                "type": "failure",
                "code": "internal:invalid-metric-name",
                "loc": ("name",),
                "summary": "Invalid metric name",
                "msg": """
                    Metric name is too long.
                    Metric names must be less than 256 characters.
                    """,
                "input": prometheus.name,
            }

    for idx, label in enumerate(prometheus.labels or ()):
        if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", label.key):
            yield {
                "type": "failure",
                "code": "internal:invalid-metric-label-name",
                "loc": ("labels", idx, "key"),
                "summary": "Invalid metric label",
                "msg": f"""
                    Label name '{label.key}' in metric '{prometheus.name}' is invalid.
                    Prometheus label names must start with an alphabetic character and can only contain alphanumeric characters and underscores (_).
                    """,
                "input": label.key,
            }

        if label.key.startswith("__"):
            yield {
                "type": "failure",
                "code": "internal:invalid-metric-label-name",
                "loc": ("labels", idx, "key"),
                "summary": "Invalid metric label",
                "msg": f"""
                    Label name '{label.key}' in metric '{prometheus.name}' is invalid.
                    Label names starts with '__' are reserved for Prometheus internal use.
                    """,
                "input": label.key,
            }

        if label.value == "":
            yield {
                "type": "warning",
                "code": "internal:invalid-metric-label-value",
                "loc": ("labels", idx, "value"),
                "summary": "Redundant metric label",
                "msg": f"""
                    Label value for label '{label.key}' in metric '{prometheus.name}' is empty.
                    Labels with an empty label value are considered equivalent to labels that do not exist.
                    """,
            }
