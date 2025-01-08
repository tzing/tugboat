from __future__ import annotations

import collections
import datetime
import logging
import typing
import xml.etree.ElementTree
from xml.etree.ElementTree import Element, ElementTree, SubElement

from tugboat.console.outputs.base import OutputBuilder
from tugboat.console.utils import format_loc

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence
    from pathlib import Path
    from typing import TextIO

    from tugboat.analyze import AugmentedDiagnosis

logger = logging.getLogger(__name__)


class JUnitOutputBuilder(OutputBuilder):

    def __init__(self):
        super().__init__()
        now = datetime.datetime.now().astimezone()
        self.root = Element("testsuites", timestamp=now.isoformat(), name="tugboat")
        self.total_counts = collections.Counter()

    def update(
        self, *, path: Path, content: str, diagnoses: Sequence[AugmentedDiagnosis]
    ) -> None:
        for manifest, manifest_diagnoses in group_by_manifest(diagnoses):
            self.write_manifest_diagnoses(
                path=path,
                manifest=manifest,
                diagnoses=manifest_diagnoses,
            )

    def write_manifest_diagnoses(
        self,
        *,
        path: Path,
        manifest: str | None,
        diagnoses: Sequence[AugmentedDiagnosis],
    ) -> None:
        # create suite for each manifest
        test_suite = SubElement(self.root, "testsuite", file=str(path))
        if manifest:
            test_suite.attrib["name"] = manifest

        # create test cases for each diagnosis
        counts = collections.Counter()
        for diagnosis in diagnoses:
            test_case = SubElement(
                test_suite,
                "testcase",
                name=diagnosis["code"],
                classname=format_loc(diagnosis["loc"]),
                file=str(path),
                line=str(diagnosis["line"]),
            )

            # the key in counts may be different from the key in the diagnosis
            match diagnosis["type"]:
                case "error":
                    counts["errors"] += 1
                case "failure":
                    counts["failures"] += 1
                case "skipped":
                    counts["skipped"] += 1
                case _:
                    logger.warning(
                        "Skip unknown diagnostic type: %s", diagnosis["type"]
                    )
                    continue

            state = SubElement(
                test_case,
                diagnosis["type"],
                message=diagnosis["summary"],
            )
            state.text = diagnosis["msg"]

        # set per-manifest counts
        test_suite.attrib.update(
            {type_: str(count) for type_, count in counts.items() if count}
        )

        # update total counts
        self.total_counts.update(counts)

    def dump(self, stream: TextIO) -> None:
        # set the counts
        self.root.attrib.update(
            {type_: str(count) for type_, count in self.total_counts.items() if count}
        )

        # write the XML
        tree = ElementTree(self.root)
        xml.etree.ElementTree.indent(tree, space="  ")
        tree.write(
            stream,
            encoding="unicode",
            xml_declaration=True,
        )


def group_by_manifest(diagnoses: Iterable[AugmentedDiagnosis]) -> Iterator[
    tuple[
        str | None,
        list[AugmentedDiagnosis],
    ]
]:
    """
    Assume that the diagnoses are sorted by manifest. Returns groups of the
    diagnoses by manifest.
    """
    manifest = None
    group = []
    for diagnosis in diagnoses:
        if diagnosis["manifest"] != manifest:
            if group:
                yield manifest, group
            manifest = diagnosis["manifest"]
            group = []
        group.append(diagnosis)
    if group:
        yield manifest, group
