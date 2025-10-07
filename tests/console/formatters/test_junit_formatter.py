import io
import textwrap
from pathlib import Path
from unittest.mock import Mock
from xml.etree.ElementTree import Element, ElementTree

import lxml.etree
from dirty_equals import DirtyEquals

from tugboat.console.formatters.junit import ElementTestCase, ElementTestSuite
from tugboat.engine import DiagnosisModel, FilesystemMetadata, ManifestMetadata

xml_parser = lxml.etree.XMLParser(remove_blank_text=True)


class TestElementTestSuite:

    def test_1(self):
        elem = ElementTestSuite(
            manifest=ManifestMetadata(kind="demo.example.com", name="test"),
            filesystem=FilesystemMetadata(filepath="/path/to/file"),
        )
        elem.append(
            ElementTestCase(
                DiagnosisModel.model_validate(
                    {
                        "line": 10,
                        "column": 11,
                        "code": "T01",
                        "loc": (),
                        "msg": "test failure",
                    }
                )
            )
        )

        assert elem == IsElementEqual(
            """
            <testsuite name="demo.example.com/test" file="/path/to/file" failures="1">
              <properties>
                <property name="kind" value="demo.example.com"/>
                <property name="name" value="test"/>
              </properties>
              <testcase classname="T01" name="." line="10" failures="1">
                <failure message="test failure">test failure</failure>
              </testcase>
            </testsuite>
            """
        )

    def test_2(self):
        elem = ElementTestSuite(
            manifest=ManifestMetadata(kind="demo.example.com", name=None),
        )
        assert elem == IsElementEqual(
            """
            <testsuite name="demo.example.com/&lt;unnamed&gt;">
              <properties>
                <property name="kind" value="demo.example.com"/>
              </properties>
            </testsuite>
            """
        )

    def test_empty(self):
        elem = ElementTestSuite(manifest=None, filesystem=None)
        assert elem == IsElementEqual(
            """
            <testsuite>
              <properties/>
            </testsuite>
            """
        )


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
            <testcase classname="T01" name=".foo.bar" line="10" file="/path/to/file" errors="1">
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
                    "code": "T02",
                    "loc": ("foo", 0),
                    "summary": "mock summary",
                    "msg": "test failure",
                }
            )
        )
        assert elem == IsElementEqual(
            """
            <testcase classname="T02" name=".foo[0]" line="10" failures="1">
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
                    "code": "T03",
                    "loc": (),
                    "summary": "mock summary",
                    "msg": "test warning",
                }
            )
        )
        assert elem == IsElementEqual(
            """
            <testcase classname="T03" name="." line="10" skipped="1">
              <skipped message="mock summary">test warning</skipped>
            </testcase>
            """
        )


class IsElementEqual(DirtyEquals[Element]):

    def __init__(self, expected: str):
        super().__init__(self.canonicalize(expected.encode()))

    @classmethod
    def canonicalize(cls, v: bytes) -> bytes:
        tree = lxml.etree.fromstring(v, parser=xml_parser)

        for node in tree.xpath("//@timestamp"):
            parent = node.getparent()
            if parent is not None:
                parent.attrib.pop(node.attrname, None)

        c14n = lxml.etree.tostring(
            tree, method="c14n", exclusive=True, with_comments=False
        )
        return c14n

    def equals(self, other):
        if isinstance(other, Element):
            with io.BytesIO() as buf:
                ElementTree(other).write(buf)
                other = buf.getvalue()
        if isinstance(other, str):
            other = other.encode()

        assert isinstance(other, bytes)
        other_c14n = self.canonicalize(other)

        (expected_c14n,) = self._repr_args
        logger.info("== COMPARING XML ==")
        logger.info("== Expected ==\n%s", expected_c14n.decode())
        logger.info("== Actual ==\n%s", other_c14n.decode())
        return expected_c14n == other_c14n
