import io
import textwrap
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree

import lxml.etree
from dirty_equals import DirtyEquals

from tugboat.console.formatters.junit import ElementTestCase, ElementTestSuite
from tugboat.engine import DiagnosisModel

xml_parser = lxml.etree.XMLParser(remove_blank_text=True)


class TestElementTestCase:

    def test_error(self):
        elem = ElementTestCase(
            DiagnosisModel.model_validate(
                {
                    "line": 10,
                    "column": 11,
                    "type": "error",
                    "code": "T01",
                    "loc": ("foo", "bar"),
                    "summary": "mock summary",
                    "msg": "test error",
                    "extras": {
                        "file": {
                            "filepath": "/path/to/file",
                        }
                    },
                }
            )
        )

        assert elem == IsElementEqual(
            """
            <testcase classname="T01" name="foo.bar" line="10" file="/path/to/file" errors="1">
              <error message="mock summary">test error</error>
            </testcase>
            """
        )

    def test_failure(self):
        elem = ElementTestCase(
            DiagnosisModel.model_validate(
                {
                    "line": 10,
                    "column": 11,
                    "type": "failure",
                    "code": "T01",
                    "loc": ("foo", "bar"),
                    "summary": "mock summary",
                    "msg": "test failure",
                }
            )
        )

        assert elem == IsElementEqual(
            """
            <testcase classname="T01" name="foo.bar" line="10" failures="1">
              <failure message="mock summary">test failure</failure>
            </testcase>
            """
        )

    def test_warning(self):
        elem = ElementTestCase(
            DiagnosisModel.model_validate(
                {
                    "line": 10,
                    "column": 11,
                    "type": "warning",
                    "code": "T01",
                    "loc": ("foo", "bar"),
                    "summary": "mock summary",
                    "msg": "test warning",
                }
            )
        )

        assert elem == IsElementEqual(
            """
            <testcase classname="T01" name="foo.bar" line="10" skipped="1">
              <skipped message="mock summary">test warning</skipped>
            </testcase>
            """
        )


class IsElementEqual(DirtyEquals[Element]):

    def __init__(self, expected: str):
        elem = lxml.etree.fromstring(expected.encode(), parser=xml_parser)
        c14n = lxml.etree.tostring(
            elem, method="c14n", exclusive=True, with_comments=False
        )
        super().__init__(c14n)

    def equals(self, other):
        if isinstance(other, Element):
            with io.BytesIO() as buf:
                ElementTree(other).write(buf)
                other = buf.getvalue()

        assert isinstance(other, bytes)
        other_elem = lxml.etree.fromstring(other, parser=xml_parser)
        other_c14n = lxml.etree.tostring(
            other_elem, method="c14n", exclusive=True, with_comments=False
        )

        return self._repr_args == (other_c14n,)
