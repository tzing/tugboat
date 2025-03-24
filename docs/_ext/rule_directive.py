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

import typing
from typing import cast

from docutils import nodes
from sphinx.addnodes import pending_xref
from sphinx.domains import Domain, ObjType
from sphinx.roles import XRefRole
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import make_refnode

if typing.TYPE_CHECKING:
    from collections.abc import Set
    from typing import Any, ClassVar

    from docutils.nodes import Element, Node, document, system_message
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


class RuleEntry(typing.NamedTuple):
    doc_name: str
    node_id: str
    rule_name: str


class RuleDirective(SphinxDirective):
    """Directive for defining a rule with code and name."""

    required_arguments = 2
    final_argument_whitespace = True
    has_content = True

    def run(self):
        # extract the rule code and name from the directive arguments
        rule_code, rule_name = self.arguments
        rule_code = rule_code.upper()

        ref_name = "tg.rule." + rule_code.lower()
        node_id = nodes.make_id(ref_name)

        # register the label in Sphinx's standard domain
        std_domain = self.env.domains.standard_domain
        std_domain.note_hyperlink_target(
            ref_name, self.env.docname, node_id, f"{rule_code} ({rule_name})"
        )

        # register the rule in tugboat domain
        tugboat_domain = cast("TugboatDomain", self.env.get_domain("tg"))
        tugboat_domain.note_rule(rule_code, rule_name, node_id)

        # create section and populate it with title and content
        title = nodes.title()
        title += [
            nodes.inline(text=rule_code, classes=["rule-code"]),
            nodes.Text(" "),
            nodes.Text(rule_name),
        ]

        section = nodes.section(classes=["rule-section"])
        section += title
        section += self.parse_content_to_nodes()

        target = nodes.target(ids=[node_id])

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
        data = domain.rules.get(rule_code)
        if data and not node.get("explicit"):
            node.clear()

            # I want to separate nodes for the rule code and name
            # The following handles the issue that pending_xref only takes the
            # first child node as the ref target
            container = nodes.inline(classes=["inline-rule-ref"])
            container += [
                nodes.inline(text=rule_code, classes=["rule-code"]),
                nodes.Text(" "),
                nodes.Text(data.rule_name),
            ]

            node += container

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

    def note_rule(self, rule_code: str, rule_name: str, node_id: str):
        self.rules[rule_code.upper()] = RuleEntry(
            doc_name=self.env.docname,
            node_id=node_id,
            rule_name=rule_name,
        )

    def get_objects(self):
        for label, (doc_name, node_id, rule_name) in self.rules.items():
            yield (label, rule_name, "rule", doc_name, node_id, 1)

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
    ) -> Element | None:
        if data := self.rules.get(target):
            return make_refnode(
                builder,
                fromdocname,
                data.doc_name,
                data.node_id,
                contnode,
                data.node_id,
            )

        return None
