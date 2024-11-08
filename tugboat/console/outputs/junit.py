from __future__ import annotations

import datetime
import logging
import typing
import xml.etree.ElementTree
from xml.etree.ElementTree import Element, ElementTree, SubElement

from tugboat.console.utils import format_loc

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path
    from typing import IO

    from tugboat.analyze import ExtendedDiagnostic

logger = logging.getLogger(__name__)


def report(
    diagnostics: dict[Path, list[ExtendedDiagnostic]],
    stream: IO[str],
) -> None:
    now = datetime.datetime.now().astimezone()
    root = Element("testsuites", timestamp=now.isoformat(), name="tugboat")

    total_counts = {"errors": 0, "failures": 0, "skipped": 0}
    for path, file_diagnostics in diagnostics.items():
        for manifest, manigest_diagnostics in group_by_manifest(file_diagnostics):
            # create a suite for each manifest
            testsuite = SubElement(root, "testsuite", file=str(path))
            if manifest:
                testsuite.attrib["name"] = manifest

            # create a test case for each diagnostic
            counts = {"errors": 0, "failures": 0, "skipped": 0}
            for diag in manigest_diagnostics:
                testcase = SubElement(
                    testsuite,
                    "testcase",
                    name=diag["code"],
                    classname=format_loc(diag["loc"]),
                    file=str(path),
                    line=str(diag["line"]),
                )

                match diag["type"]:
                    case "error":
                        state = SubElement(testcase, "error", message=diag["summary"])
                        counts["errors"] += 1
                    case "failure":
                        state = SubElement(testcase, "failure", message=diag["summary"])
                        counts["failures"] += 1
                    case "skipped":
                        state = SubElement(testcase, "skipped", message=diag["summary"])
                        counts["skipped"] += 1
                    case _:
                        logger.warning("Skip unknown diagnostic type: %s", diag["type"])
                        continue

                state.text = diag["msg"]

            # update the counts for the suite
            testsuite.attrib.update(
                {type_: str(count) for type_, count in counts.items() if count}
            )

            # update the counts for the total report
            for type_, count in counts.items():
                total_counts[type_] += count

    # update the counts for the total report
    root.attrib.update(
        {type_: str(count) for type_, count in total_counts.items() if count}
    )

    # write the XML
    tree = ElementTree(root)
    xml.etree.ElementTree.indent(tree, space="  ")
    tree.write(
        stream,
        encoding="unicode",
        xml_declaration=True,
    )


def group_by_manifest(
    diagnostics: Iterable[ExtendedDiagnostic],
) -> Iterator[
    tuple[
        str | None,
        list[ExtendedDiagnostic],
    ]
]:
    """
    Assume that the diagnostics are sorted by manifest. Returns groups of the
    diagnostics by manifest.
    """
    manifest = None
    group = []
    for diag in diagnostics:
        if diag["manifest"] != manifest:
            if group:
                yield manifest, group
            manifest = diag["manifest"]
            group = []
        group.append(diag)
    if group:
        yield manifest, group
