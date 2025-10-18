import io
import logging
from xml.etree.ElementTree import Element, ElementTree

import lxml.etree
from dirty_equals import DirtyEquals

from tugboat.console.formatters.junit import (
    ElementTestCase,
    ElementTestSuite,
    JUnitFormatter,
)
from tugboat.engine import (
    DiagnosisModel,
    FilesystemMetadata,
    HelmMetadata,
    ManifestMetadata,
)
from tugboat.engine.types import Extras

logger = logging.getLogger(__name__)
xml_parser = lxml.etree.XMLParser(remove_blank_text=True)


class TestJUnitFormatter:

    def test(self):
        diagnosis_data = {
            "line": 1,
            "column": 1,
            "code": "T01",
            "loc": (),
            "msg": "test",
        }

        formatter = JUnitFormatter()
        formatter.update(
            content="",
            diagnoses=[
                # GROUP A: three exactly same diagnoses (one left for later)
                *[
                    DiagnosisModel.model_validate(
                        {
                            **diagnosis_data,
                            "extras": Extras(
                                file=FilesystemMetadata(
                                    filepath="manifest.yaml",
                                ),
                                helm=HelmMetadata(
                                    chart="my-chart",
                                    template="templates/diagnoses.yaml",
                                ),
                                manifest=ManifestMetadata(
                                    group="example.com",
                                    kind="Demo",
                                    name="diagnoses",
                                ),
                            ),
                        }
                    )
                ]
                * 2,
                # GROUP B: different filepath
                DiagnosisModel.model_validate(
                    {
                        **diagnosis_data,
                        "type": "error",
                        "extras": Extras(
                            file=FilesystemMetadata(
                                filepath="another-manifest.yaml",
                            ),
                            helm=None,
                            manifest=ManifestMetadata(
                                group="example.com",
                                kind="Demo",
                                name="diagnoses",
                            ),
                        ),
                    }
                ),
                # GROUP C: different manifest name
                DiagnosisModel.model_validate(
                    {
                        **diagnosis_data,
                        "extras": Extras(
                            file=FilesystemMetadata(
                                filepath="manifest.yaml",
                            ),
                            helm=None,
                            manifest=ManifestMetadata(
                                group="example.com",
                                kind="Demo",
                                name="other-diagnoses",
                            ),
                        ),
                    }
                ),
                # GROUP A
                DiagnosisModel.model_validate(
                    {
                        **diagnosis_data,
                        "extras": Extras(
                            file=FilesystemMetadata(
                                filepath="manifest.yaml",
                            ),
                            helm=None,
                            manifest=ManifestMetadata(
                                group="example.com",
                                kind="Demo",
                                name="diagnoses",
                            ),
                        ),
                    }
                ),
                # GROUP D: different manifest kind
                DiagnosisModel.model_validate(
                    {
                        **diagnosis_data,
                        "extras": Extras(
                            file=FilesystemMetadata(
                                filepath="manifest.yaml",
                            ),
                            helm=None,
                            manifest=ManifestMetadata(
                                group="example.com",
                                kind="Another",
                                name="diagnoses",
                            ),
                        ),
                    }
                ),
                # GROUP E: no path and manifest (stdin must be ignored)
                DiagnosisModel.model_validate(
                    {
                        **diagnosis_data,
                        "type": "error",
                        "extras": Extras(
                            file=FilesystemMetadata(
                                filepath="<stdin>",
                            ),
                            helm=None,
                            manifest=None,
                        ),
                    }
                ),
            ],
        )

        with io.StringIO() as buf:
            formatter.dump(buf)
            output = buf.getvalue()

        assert output == IsElementEqual(
            """<?xml version='1.0' encoding='utf-8'?>
            <testsuites name="tugboat" errors="2" failures="5">

              <!-- GROUP A: three exactly same diagnoses -->
              <testsuite name="demo.example.com/diagnoses" file="manifest.yaml" failures="3">
                <properties>
                  <property name="string:helm-chart" value="my-chart"/>
                  <property name="string:helm-template" value="templates/diagnoses.yaml"/>
                  <property name="string:manifest-kind" value="demo.example.com"/>
                  <property name="string:manifest-name" value="diagnoses"/>
                </properties>
                <testcase name="." classname="T01" failures="1" file="manifest.yaml" line="1"><failure message="test">test</failure></testcase>
                <testcase name="." classname="T01" failures="1" file="manifest.yaml" line="1"><failure message="test">test</failure></testcase>
                <testcase name="." classname="T01" failures="1" file="manifest.yaml" line="1"><failure message="test">test</failure></testcase>
              </testsuite>

              <!-- GROUP B: different filepath -->
              <testsuite name="demo.example.com/diagnoses" file="another-manifest.yaml" errors="1">
                <properties>
                  <property name="string:manifest-kind" value="demo.example.com"/>
                  <property name="string:manifest-name" value="diagnoses"/>
                </properties>
                <testcase classname="T01" errors="1" file="another-manifest.yaml" line="1" name="."><error message="test">test</error></testcase>
              </testsuite>

              <!-- GROUP C: different manifest name -->
              <testsuite name="demo.example.com/other-diagnoses" file="manifest.yaml" failures="1">
                <properties>
                  <property name="string:manifest-kind" value="demo.example.com"/>
                  <property name="string:manifest-name" value="other-diagnoses"/>
                </properties>
                <testcase name="." classname="T01" failures="1" file="manifest.yaml" line="1"><failure message="test">test</failure></testcase>
              </testsuite>

              <!-- GROUP D: different manifest kind -->
              <testsuite name="another.example.com/diagnoses" file="manifest.yaml" failures="1">
                <properties>
                  <property name="string:manifest-kind" value="another.example.com"/>
                  <property name="string:manifest-name" value="diagnoses"/>
                </properties>
                <testcase name="." classname="T01" failures="1" file="manifest.yaml" line="1"><failure message="test">test</failure></testcase>
              </testsuite>

              <!-- GROUP E: missing path and manifest -->
              <testsuite errors="1">
                <properties/>
                <testcase classname="T01" errors="1" line="1" name="."><error message="test">test</error></testcase>
              </testsuite>

            </testsuites>
            """
        )


class TestElementTestSuite:

    def test_1(self):
        elem = ElementTestSuite(
            manifest=ManifestMetadata(group="example.com", kind="Demo", name="test"),
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
                <property name="string:manifest-kind" value="demo.example.com"/>
                <property name="string:manifest-name" value="test"/>
              </properties>
              <testcase classname="T01" name="." line="10" failures="1">
                <failure message="test failure">test failure</failure>
              </testcase>
            </testsuite>
            """
        )

    def test_2(self):
        elem = ElementTestSuite(
            manifest=ManifestMetadata(group="example.com", kind="Demo", name=None),
        )
        assert elem == IsElementEqual(
            """
            <testsuite name="demo.example.com/&lt;unnamed&gt;">
              <properties>
                <property name="string:manifest-kind" value="demo.example.com"/>
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
        logger.info(
            "=== COMPARING XML ===\n--- expect\n+++ actual\n@@ -1 +1 @@\n-%s\n+%s",
            expected_c14n.decode(),
            other_c14n.decode(),
        )
        return expected_c14n == other_c14n
