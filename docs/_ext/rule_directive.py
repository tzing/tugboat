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

   :ref:`tugboat.rule.RULE-ID`
"""

from __future__ import annotations

import typing
from typing import cast
from docutils import nodes
from sphinx.util.docutils import SphinxDirective

if typing.TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.domains.std import StandardDomain
    from sphinx.environment import BuildEnvironment


def setup(app: Sphinx):
    app.add_directive("rule", RuleDirective)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }


class RuleDirective(SphinxDirective):
    """Directive for defining a rule with code and name."""

    required_arguments = 2
    final_argument_whitespace = True
    has_content = True

    def run(self):
        # extract the rule code and name from the directive arguments
        rule_code, rule_name = self.arguments
        rule_code = rule_code.upper()

        anchor = "tugboat.rule." + rule_code.lower()
        anchor_id = nodes.make_id(anchor)

        # check for duplicate labels and warn if found
        env = cast("BuildEnvironment", self.state.document.settings.env)
        std_domain = cast("StandardDomain", env.get_domain("std"))
        if anchor in std_domain.labels:
            other_doc = env.doc2path(std_domain.labels[anchor][0])
            reporter = self.state.document.reporter
            reporter.warning(
                f"Duplicate label '{anchor_id}' already defined in {other_doc}",
                line=self.lineno,
            )

        # register the label in Sphinx's standard domain
        doc_name = env.docname
        std_domain.labels[anchor] = (doc_name, anchor_id, f"{rule_code} ({rule_name})")
        std_domain.anonlabels[anchor] = (doc_name, anchor_id)

        # create section and populate it with title and content
        title = nodes.title()
        title += [
            nodes.inline(text=rule_code, classes=["rule-code"]),
            nodes.inline(text=" - ", classes=["rule-separator"]),
            nodes.inline(text=rule_name, classes=["rule-name"]),
        ]

        section = nodes.section(classes=["rule-section"])
        section += title
        section += self.parse_content_to_nodes()

        target = nodes.target(ids=[anchor_id])

        return [target, section]
