import io

import pytest

import tugboat.settings
from tugboat.console.formatters import get_output_formatter
from tugboat.engine import DiagnosisModel


def test(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(tugboat.settings.settings, "output_format", "github")

    formatter = get_output_formatter()
    formatter.update(
        content="",
        diagnoses=[
            DiagnosisModel.model_validate(
                {
                    "type": "error",
                    "line": 1,
                    "column": 1,
                    "code": "T01",
                    "loc": (),
                    "summary": "mock:error",
                    "msg": "test",
                }
            ),
            DiagnosisModel.model_validate(
                {
                    "type": "warning",
                    "line": 1,
                    "column": 1,
                    "code": "T02",
                    "loc": (),
                    "summary": "mock warning",
                    "msg": "test\nwith new line",
                    "extras": {
                        "file": {
                            "filepath": "test.txt",
                        },
                    },
                }
            ),
        ],
    )

    with io.StringIO() as buf:
        formatter.dump(buf)
        output = buf.getvalue()

    assert output == (
        "::error line=1,title=T01 (mock%3Aerror)::test\n"
        "::warning file=test.txt,line=1,title=T02 (mock warning)::test%0Awith new line\n"
    )
