from dirty_equals import IsPartialDict

from tests.utils import ContainsSubStrings
from tugboat.analyzers.kubernetes import check_resource_name


class TestCheckResourceName:

    def test_pass(self):
        assert check_resource_name("valid-name") is None
        assert check_resource_name("valid-name-", is_generate_name=True) is None

    def test_fail_too_long(self):
        assert check_resource_name("abcde", length=4) == IsPartialDict(
            {
                "code": "M009",
                "msg": "Resource name 'abcde' is too long, maximum length is 4.",
            }
        )

    def test_fail_invalid__name(self):
        assert check_resource_name("invalid_name") == IsPartialDict(
            {
                "code": "M010",
                "msg": ContainsSubStrings("Resource name 'invalid_name' is invalid."),
                "fix": "invalid-name",
            }
        )

        assert check_resource_name("name-") == IsPartialDict(
            {
                "code": "M010",
                "msg": ContainsSubStrings("Resource name 'name-' is invalid."),
            }
        )

    def test_fail_invalid__generatename(self):
        diagnostic = check_resource_name("invalid_name-", is_generate_name=True)
        assert diagnostic == IsPartialDict(
            {
                "code": "M010",
                "msg": ContainsSubStrings("Resource name 'invalid_name-' is invalid."),
                "fix": "invalid-name-",
            }
        )

    def test_empty(self):
        diagnostic = check_resource_name("", is_generate_name=True)
        assert diagnostic == IsPartialDict(
            {
                "code": "M010",
                "msg": ContainsSubStrings("Resource name '' is invalid."),
                "input": "",
            }
        )
