from unittest.mock import Mock

import lark
import pytest
from dirty_equals import IsPartialDict, IsStr

from tests.dirty_equals import HasSubstring
from tugboat.analyzers.template_tag import (
    check_simple_tag_reference,
    check_template_tags,
    parse_argo_template_tags,
    split_expr_membership,
)
from tugboat.references import ReferenceCollection


class TestParseArgoTemplateTags:

    def test_pass(self):
        tree = parse_argo_template_tags(
            """
            Hello {{ inputs.parameters.name }}
            This is {{ inputs.parameters['bot'] }} speaking.

            The result is {{= 1 + 2 }}.
            """
        )

        (input_name_tag, bot_name_tag) = tree.find_data("simple_tag")

        (input_name,) = input_name_tag.find_token("REF")
        assert input_name == "inputs.parameters.name"

        (bot_name,) = bot_name_tag.find_token("REF")
        assert bot_name == "inputs.parameters['bot']"

    def test_error(self):
        with pytest.raises(lark.exceptions.UnexpectedCharacters):
            parse_argo_template_tags("{{ inputs. parameters.name }}")
        with pytest.raises(lark.exceptions.UnexpectedEOF):
            parse_argo_template_tags("{{ inputs.parameters.name ")


class TestCheckTemplateTags:

    def test_pass(self):
        references = ReferenceCollection()
        references.add(("inputs", "parameters", "name"))

        diagnoses = list(
            check_template_tags("{{ inputs.parameters.name }}", references)
        )

        assert diagnoses == []

    def test_unexpected_character(self):
        diagnoses = list(
            check_template_tags(
                "{{ inputs. parameters.name }}",
                Mock(ReferenceCollection),
            )
        )
        assert diagnoses == [
            IsPartialDict(
                code="VAR101",
                summary="Syntax error",
                msg=(
                    IsStr()
                    & HasSubstring("The field contains a syntax error")
                    & HasSubstring("{{ inputs. parameters.name }}")
                    & HasSubstring("This error is usually caused by invalid characters")
                ),
            )
        ]

    def test_unexpected_eof(self):
        diagnoses = list(
            check_template_tags(
                "{{ inputs",
                Mock(ReferenceCollection),
            )
        )
        assert diagnoses == [
            IsPartialDict(
                code="VAR101",
                summary="Syntax error",
                msg=(
                    IsStr()
                    & HasSubstring("The field contains a syntax error")
                    & HasSubstring("{{ inputs")
                    & HasSubstring(
                        "This error is usually caused by an incomplete template tag"
                    )
                ),
            )
        ]


class TestCheckSimpleTagReference:

    def test_pass(self):
        references = ReferenceCollection()
        references.add(("inputs", "parameters", "name"))

        diagnosis = check_simple_tag_reference("inputs.parameters.name", references)
        assert diagnosis is None

    def test_incorrect_format(self):
        references = ReferenceCollection()
        references.add(("inputs", "parameters", "name"))

        diagnosis = check_simple_tag_reference("inputs.parameters['name']", references)

        assert diagnosis == IsPartialDict(
            code="VAR102",
            summary="Incorrect template tag format",
            fix="inputs.parameters.name",
        )

    def test_syntax_error(self):
        references = ReferenceCollection()
        diagnosis = check_simple_tag_reference("inputs.parameters['name", references)
        assert diagnosis == IsPartialDict(code="VAR101")


class TestSplitExprMembership:

    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            # success
            ("parameters", ("parameters",)),
            ("parameters.item", ("parameters", "item")),
            ("parameters['item-1'].subkey", ("parameters", "item-1", "subkey")),
            ('parameters["item-2"].subkey', ("parameters", "item-2", "subkey")),
            ("a.b.c['d'].e['f'].g", ("a", "b", "c", "d", "e", "f", "g")),
            # failed
            ("0", ()),
            ("parameters[\"item']", ()),
        ],
    )
    def test(self, source: str, expected: tuple[str, ...]):
        parts = split_expr_membership(source)
        assert parts == expected
