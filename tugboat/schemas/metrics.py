from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from tugboat.schemas.basic import Array, KeyValuePair


class _BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Metrics(_BaseModel):
    """
    `Metrics`_ are a list of metrics emitted from a :py:class:`~tugboat.schemas.workflow.Workflow`
    or :py:class:`~tugboat.schemas.template.Template`.

    .. _Metrics: https://argo-workflows.readthedocs.io/en/latest/fields/#metrics
    """

    prometheus: Array[Prometheus]


class Prometheus(_BaseModel):
    """
    `Prometheus`_ is a prometheus metric to be emitted.

    .. _Prometheus: https://argo-workflows.readthedocs.io/en/latest/fields/#prometheus
    """

    counter: Counter | None = None
    gauge: Gauge | None = None
    help: str
    histogram: Histogram | None = None
    labels: Array[KeyValuePair] | None = None
    name: str
    when: str | None = None


class Counter(_BaseModel):
    """
    `Counter` is a `prometheus counter`_ metric.

    .. _Counter: https://argo-workflows.readthedocs.io/en/latest/fields/#counter
    .. _prometheus counter: https://prometheus.io/docs/concepts/metric_types/#counter
    """

    value: str


class Gauge(_BaseModel):
    """
    `Gauge`_ is a `prometheus gauge`_  metric.

    .. _Gauge: https://argo-workflows.readthedocs.io/en/latest/fields/#gauge
    .. _prometheus gauge: https://prometheus.io/docs/concepts/metric_types/#gauge
    """

    operation: str | None = None
    realtime: bool | None = None
    value: str


class Histogram(_BaseModel):
    """
    `Histogram`_ is a `prometheus histogram`_ metric.

    .. _Histogram: https://argo-workflows.readthedocs.io/en/latest/fields/#histogram
    .. _prometheus histogram: https://prometheus.io/docs/concepts/metric_types/#histogram
    """

    buckets: Array[int | float]
    value: str
