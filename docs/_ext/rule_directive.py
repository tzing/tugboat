"""
This module provides a directive for the Sphinx documentation system that
allows the user to write rules in a more simple and readable format.

The rule directive supports the following syntax::

   .. rule:: RULE-ID Rule Name

      Rule description blah blah blah

The rule directive will be rendered as a section with a title that contains
the rule ID and the rule name.

The rule directive will also add a target to the rule ID for cross-referencing.
For referencing the rule, you can leverage the following syntax::

   :ref:`tg.rule.RULE-ID`
"""

from __future__ import annotations

import functools
import typing
from dataclasses import dataclass
from types import SimpleNamespace
from typing import cast

import docutils.frontend
from docutils import nodes
from docutils.parsers.rst import Parser
from docutils.parsers.rst.states import Inliner
from docutils.utils import new_document
from sphinx.addnodes import pending_xref
from sphinx.domains import Domain, ObjType
from sphinx.roles import XRefRole
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import make_refnode

if typing.TYPE_CHECKING:
    from collections.abc import Set
    from typing import Any, ClassVar

    from docutils.nodes import Element, Node, document, reference, system_message
    from sphinx.application import Sphinx
    from sphinx.builders import Builder
    from sphinx.environment import BuildEnvironment


def setup(app: Sphinx):
    app.add_domain(TugboatDomain)

    # shortcut for using the rule directive and role
    app.add_directive("rule", RuleDirective)
    app.add_role("rule", RuleRole(nodeclass=pending_xref))

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }


@dataclass(frozen=True)
class RuleEntry:

    code: str
    title: str
    doc_name: str

    def __post_init__(self):
        object.__setattr__(self, "code", self.code.upper())

    @functools.cached_property
    def ref_name(self) -> str:
        return "tg.rule." + self.code.lower()

    @functools.cached_property
    def node_id(self) -> str:
        return nodes.make_id(self.ref_name)

    def title_nodes(self) -> list[Node]:
        settings = docutils.frontend.get_default_settings(Parser())
        doc = new_document("<rule-title>", settings=settings)

        inliner = Inliner()
        inliner.init_customizations(settings)
        memo = SimpleNamespace(document=doc, reporter=doc.reporter, language=None)

        text_nodes, _ = inliner.parse(self.title, 1, memo, doc)
        return text_nodes

    def title_stripped(self) -> str:
        return "".join(node.astext() for node in self.title_nodes())

    def node(self):
        """Create reference node for this rule."""
        container = nodes.inline(classes=["inline-rule-ref"])
        container += [
            nodes.inline(text=self.code, classes=["rule-code"]),
            nodes.Text(" "),
            *self.title_nodes(),
        ]
        return container


class RuleDirective(SphinxDirective):
    """Directive for defining a rule with code and name."""

    required_arguments = 2
    final_argument_whitespace = True
    has_content = True

    def run(self):
        # extract the rule code and name from the directive arguments
        rule_code, rule_name = self.arguments
        rule_code = rule_code.upper()

        # register the rule in tugboat domain
        tugboat_domain = cast("TugboatDomain", self.env.get_domain("tg"))
        entry = tugboat_domain.note_rule(rule_code, rule_name)

        # create section and populate it with title and content
        rule_name_nodes, _ = self.parse_inline(rule_name)

        title = nodes.title(classes=["rule-title"])
        title += [
            nodes.inline(text=rule_code, classes=["rule-code"]),
            nodes.Text(" "),
            *rule_name_nodes,
        ]

        section = nodes.section(classes=["rule-section"])
        section += title
        section += self.parse_content_to_nodes()

        target = nodes.target(ids=[entry.node_id])

        return [target, section]


class RuleRole(XRefRole):
    """
    A cross-reference role for customizing Tugboat rule references in Sphinx
    documentation.
    """

    def process_link(
        self,
        env: BuildEnvironment,
        refnode: Element,
        has_explicit_title: bool,
        title: str,
        target: str,
    ) -> tuple[str, str]:
        # this role is added to the standard domain, so we need to set the
        # reference domain to "tg" to ensure that the reference is resolved
        # correctly
        refnode["refdomain"] = "tg"
        refnode["refwarn"] = True
        return title, target.upper()

    def result_nodes(
        self,
        document: document,
        env: BuildEnvironment,
        node: Element,
        is_ref: bool,
    ) -> tuple[list[Node], list[system_message]]:
        rule_code: str = node["reftarget"]

        domain = cast("TugboatDomain", env.get_domain("tg"))
        entry = domain.rules.get(rule_code.upper())

        if entry and not node.get("explicit"):
            node.clear()
            node += entry.node()

        return [node], []


class TugboatDomain(Domain):

    name = "tg"
    label = "Tugboat"

    directives: ClassVar = {"rule": RuleDirective}
    roles: ClassVar = {"rule": RuleRole()}
    object_types: ClassVar = {"rule": ObjType("Tugboat rule", "ref")}

    @property
    def rules(self) -> dict[str, RuleEntry]:
        return self.data.setdefault("rules", {})

    def note_rule(self, rule_code: str, rule_name: str) -> RuleEntry:
        """
        Note a rule in the domain.

        Parameters
        ----------
        rule_code : str
            The unique code for the rule.
        rule_name : str
            The name of the rule.

        Returns
        -------
        entry : RuleEntry
            The registered rule entry.
        """
        # register a rule in this domain
        entry = RuleEntry(
            code=rule_code,
            title=rule_name,
            doc_name=self.env.docname,
        )

        self.rules[entry.code] = entry

        # register the label in Sphinx's standard domain
        std_domain = self.env.domains.standard_domain
        std_domain.note_hyperlink_target(
            name=entry.ref_name,
            docname=self.env.docname,
            node_id=entry.node_id,
            title=f"{entry.code} ({entry.title_stripped()})",
        )

        return entry

    def get_objects(self):
        for label, rule in self.rules.items():
            yield (label, rule.title, "rule", rule.doc_name, rule.node_id, 1)

    def clear_doc(self, docname: str):
        to_remove = []
        for rule_code, data in self.rules.items():
            if data.doc_name == docname:
                to_remove.append(rule_code)
        for rule_code in to_remove:
            self.rules.pop(rule_code)

    def merge_domaindata(self, docnames: Set[str], otherdata: dict[str, Any]):
        for rule_code, data in otherdata.get("rules", {}).items():
            if data.doc_name in docnames:
                self.rules[rule_code] = data

    def resolve_xref(
        self,
        env: BuildEnvironment,
        fromdocname: str,
        builder: Builder,
        typ: str,
        target: str,
        node: pending_xref,
        contnode: Element,
    ) -> reference | None:
        if entry := self.rules.get(target):
            return make_refnode(
                builder,
                fromdocname,
                entry.doc_name,
                entry.node_id,
                entry.node(),
                entry.title,
            )

        return None
