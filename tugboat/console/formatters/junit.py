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


class ElementTestCase(Element):
    """<testcase> element = a single diagnosis"""

    def __init__(self, diagnosis: DiagnosisModel):
        # create <testcase> element
        attrib = {
            "name": diagnosis.loc_path[1:],  # skip the leading dot
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
