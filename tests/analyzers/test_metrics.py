from dirty_equals import IsPartialDict

from tests.dirty_equals import ContainsSubStrings
from tugboat.analyzers.metrics import check_prometheus
from tugboat.references import Context
from tugboat.schemas.metrics import Prometheus


class TestCheckPrometheus:

    def test_fields(self):
        prom = Prometheus.model_validate(
            {
                "name": "test_metric",
                "help": "",
                "counter": {
                    "value": "1",
                },
                "gauge": {
                    "value": "1",
                },
            }
        )

        diagnoses = list(check_prometheus(prom, Context()))
        assert diagnoses == [
            IsPartialDict({"code": "M202", "loc": ("help",)}),
            IsPartialDict({"code": "M201", "loc": ("counter",)}),
            IsPartialDict({"code": "M201", "loc": ("gauge",)}),
        ]

    def test_invalid_metric_name(self):
        prom = Prometheus.model_validate(
            {
                "name": "test/metric",
                "help": "some help",
                "counter": {
                    "value": "1",
                },
            }
        )

        diagnoses = list(check_prometheus(prom, Context()))
        assert diagnoses == [
            IsPartialDict(
                {
                    "code": "internal:invalid-metric-name",
                    "loc": ("name",),
                    "msg": ContainsSubStrings("Metric name 'test/metric' is invalid."),
                    "input": "test/metric",
                }
            ),
        ]

    def test_invalid_label_names(self):
        prom = Prometheus.model_validate(
            {
                "name": "test_metric",
                "help": "some help",
                "labels": [
                    {"key": "test/label", "value": "foo"},
                    {"key": "__reserved", "value": "bar"},
                    {"key": "valid_label", "value": ""},
                ],
                "counter": {
                    "value": "1",
                },
            }
        )

        diagnoses = list(check_prometheus(prom, Context()))
        assert diagnoses == [
            IsPartialDict(
                {
                    "code": "internal:invalid-metric-label-name",
                    "loc": ("labels", 0, "key"),
                    "msg": ContainsSubStrings(
                        "Label name 'test/label' in metric 'test_metric' is invalid."
                    ),
                    "input": "test/label",
                }
            ),
            IsPartialDict(
                {
                    "code": "internal:invalid-metric-label-name",
                    "loc": ("labels", 1, "key"),
                    "msg": ContainsSubStrings(
                        "Label name '__reserved' in metric 'test_metric' is invalid."
                    ),
                    "input": "__reserved",
                }
            ),
            IsPartialDict(
                {
                    "code": "internal:invalid-metric-label-value",
                    "loc": ("labels", 2, "value"),
                    "msg": ContainsSubStrings(
                        "Label value for label 'valid_label' in metric 'test_metric' is empty."
                    ),
                },
            ),
        ]
