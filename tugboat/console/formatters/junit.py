from __future__ import annotations

import collections
import datetime
import logging
import typing
from xml.etree.ElementTree import Element, SubElement

from tugboat.console.formatters.base import OutputFormatter

if typing.TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path
    from typing import Self

    from tugboat.engine import DiagnosisModel, FilesystemMetadata, ManifestMetadata


logger = logging.getLogger(__name__)


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
