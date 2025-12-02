from unittest.mock import Mock

import lark
import pytest
from dirty_equals import IsPartialDict, IsStr

from tests.dirty_equals import HasSubstring
from tugboat.analyzers.template_tag import check_template_tags, parse_argo_template_tags
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
