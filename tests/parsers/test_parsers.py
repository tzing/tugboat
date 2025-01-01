from unittest.mock import Mock

from dirty_equals import IsPartialDict

from tugboat.parsers import Node, Unexpected, parse_template, report_syntax_errors
from tugboat.parsers.ast.argo_template import Document


class TestParseTemplate:
    def test(self):
        doc = parse_template("Hello, {{ node.name }}!")
        assert isinstance(doc, Document)


class TestReportSyntaxErrors:

    def test_no_error(self):
        node = Mock(
            Node,
            children=[
                Mock(Node, children=[]),
                Mock(
                    Node,
                    children=[
                        Mock(Node, children=[]),
                    ],
                ),
            ],
        )
        assert list(report_syntax_errors(node)) == []

    def test_childless(self):
        node = Mock(Node, children=[])
        assert list(report_syntax_errors(node)) == []

    def test_errors(self):
        node = Mock(
            Node,
            children=[
                Mock(Unexpected, text="foo", msg=None, children=[]),
                Mock(Unexpected, text="bar", msg="test error", children=[]),
                Mock(Unexpected, text="baz", msg=None, children=[]),
                Mock(Unexpected, text="qux", msg=None, children=[]),
            ],
        )

        assert list(report_syntax_errors(node)) == [
            IsPartialDict(
                {
                    "code": "VAR001",
                    "loc": (),
                    "summary": "Syntax error",
                    "input": "foo",
                }
            )
        ]

    def test_nested_error(self):
        node = Mock(
            Node,
            children=[
                Mock(Node, children=[]),
                Mock(
                    Node,
                    children=[
                        Mock(Unexpected, text="test", msg="test error", children=[]),
                    ],
                ),
            ],
        )

        assert list(report_syntax_errors(node)) == [
            {
                "code": "VAR001",
                "loc": (),
                "summary": "Syntax error",
                "msg": "Invalid syntax near 'test': test error",
                "input": "test",
            },
        ]
