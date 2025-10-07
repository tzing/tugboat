from __future__ import annotations

import collections
import datetime
import logging
import typing
from xml.etree.ElementTree import Element, ElementTree, SubElement

from tugboat.console.formatters.base import OutputFormatter

if typing.TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import TextIO

    from tugboat.engine import DiagnosisModel, FilesystemMetadata, ManifestMetadata


logger = logging.getLogger(__name__)


class JUnitFormatter(OutputFormatter):

    def __init__(self):
        super().__init__()
        self.testsuites: dict[tuple[str | None, str | None], ElementTestSuite] = {}

    def update(self, *, content: str, diagnoses: Sequence[DiagnosisModel]) -> None:
        for diagnosis in diagnoses:
            # find or create the appropriate testsuite element
            file_path = None
            if diagnosis.extras.file:
                file_path = diagnosis.extras.file.filepath

            manifest_name = None
            if diagnosis.extras.manifest:
                manifest_name = (
                    f"{diagnosis.extras.manifest.kind}/{diagnosis.extras.manifest.name}"
                )

            key = (file_path, manifest_name)
            if key not in self.testsuites:
                self.testsuites[key] = ElementTestSuite(
                    manifest=diagnosis.extras.manifest,
                    filesystem=diagnosis.extras.file,
                )

            testsuite = self.testsuites[key]

            # create a testcase element for this diagnosis
            testcase = ElementTestCase(diagnosis)
            testsuite.append(testcase)

    def dump(self, stream: TextIO) -> None:
        # create root <testsuites> element
        now = datetime.datetime.now().astimezone()
        attrib = {
            "name": "tugboat",
            "timestamp": now.isoformat(),
        }

        counter = collections.Counter()
        for testsuite in self.testsuites.values():
            for stat_name, count in testsuite.counter.items():
                counter[stat_name] += count

        for stat_name, count in counter.items():
            attrib[stat_name] = str(count)

        testsuites = Element("testsuites", attrib)

        # append all <testsuite> elements
        for testsuite in self.testsuites.values():
            testsuites.append(testsuite)

        # serialize <testsuites> element
        tree = ElementTree(testsuites)
        tree.write(stream, encoding="unicode", xml_declaration=True)


class ElementTestSuite(Element):
    """<testsuite> element = a manifest"""

    def __init__(
        self,
        manifest: ManifestMetadata | None = None,
        filesystem: FilesystemMetadata | None = None,
    ):
        # create <testsuite> element
        now = datetime.datetime.now().astimezone()
        attrib = {
            "timestamp": now.isoformat(),
        }

        if manifest:
            if manifest.name:
                attrib["name"] = f"{manifest.kind}/{manifest.name}"
            else:
                attrib["name"] = f"{manifest.kind}/<unnamed>"

        if filesystem:
            attrib["file"] = filesystem.filepath

        super().__init__("testsuite", attrib)

        # internal counter for statistics
        self.counter = collections.Counter()

        # create <properties> element
        properties = SubElement(self, "properties")

        if manifest:
            SubElement(properties, "property", {"name": "kind", "value": manifest.kind})
            if manifest.name:
                SubElement(
                    properties, "property", {"name": "name", "value": manifest.name}
                )

    def append(self, subelement):
        if isinstance(subelement, ElementTestCase):
            self.counter[subelement.stat_name] += 1
            for stat_name, count in self.counter.items():
                self.attrib[stat_name] = str(count)

        return super().append(subelement)


class ElementTestCase(Element):
    """<testcase> element = a single diagnosis"""

    def __init__(self, diagnosis: DiagnosisModel):
        # create <testcase> element
        attrib = {
            "name": diagnosis.loc_path,
            "classname": diagnosis.code,
            "line": str(diagnosis.line),
        }

        if diagnosis.extras.file:
            attrib["file"] = diagnosis.extras.file.filepath

        super().__init__("testcase", attrib)

        # determine result type
        match diagnosis.type:
            case "error":
                result_name = "error"
                stat_name = "errors"
            case "failure":
                result_name = "failure"
                stat_name = "failures"
            case "warning":
                result_name = "skipped"
                stat_name = "skipped"

        self.stat_name = stat_name
        self.attrib[stat_name] = "1"

        # create result element
        result_element = SubElement(self, result_name, {"message": diagnosis.summary})
        result_element.text = diagnosis.msg
