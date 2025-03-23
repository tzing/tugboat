from dirty_equals import IsPartialDict

from tests.dirty_equals import ContainsSubStrings
from tugboat.analyzers.kubernetes import check_resource_name


class TestCheckResourceName:

    def test_pass(self):
        assert list(check_resource_name("valid-name")) == []
        assert list(check_resource_name("valid-name-", is_generate_name=True)) == []

    def test_fail_length(self):
        # min length - name
        assert IsPartialDict(
            {
                "code": "M302",
                "msg": "Resource name 'abcde' is too short, minimum length is 10.",
            }
        ) in check_resource_name("abcde", min_length=10)

        # min length - generate name
        assert IsPartialDict(
            {
                "code": "M302",
                "msg": "Resource name 'abcd' is too short, minimum length is 5.",
            }
        ) in check_resource_name("abcd", min_length=10, is_generate_name=True)

        # min length - generate name - almost empty
        diagnoses = check_resource_name("t", is_generate_name=True)
        assert list(diagnoses) == []

        # min length - empty
        diagnoses = list(check_resource_name("", is_generate_name=True))
        assert (
            IsPartialDict(
                {
                    "code": "M302",
                    "msg": "Resource name is empty, minimum length is 1.",
                }
            )
            in diagnoses
        )

        # max length - name
        assert IsPartialDict(
            {
                "code": "M302",
                "msg": "Resource name 'abcde' is too long, maximum length is 4.",
            }
        ) in check_resource_name("abcde", max_length=4)

        # max length - generate name
        assert IsPartialDict(
            {
                "code": "M302",
                "msg": "Resource name 'abcd-' is too long, maximum length is 4.",
            }
        ) in check_resource_name("abcd-", max_length=9, is_generate_name=True)

    def test_fail_invalid__name(self):
        # invalid characters
        assert IsPartialDict(
            {
                "code": "M301",
                "msg": ContainsSubStrings(
                    "Resource name 'invalid_name' contains invalid characters."
                ),
                "fix": "invalid-name",
            }
        ) in check_resource_name("invalid_name")

        # suffix `-` for name is not allowed
        assert IsPartialDict(
            {
                "code": "M301",
                "msg": ContainsSubStrings(
                    "Resource name 'name-' contains invalid characters."
                ),
            }
        ) in check_resource_name("name-")

        # suffix `-` for generate name is allowed
        assert list(check_resource_name("name-", is_generate_name=True)) == []

        # check alternative name
        assert IsPartialDict(
            {
                "code": "M301",
                "msg": ContainsSubStrings(
                    "Resource name 'invalid_name-' contains invalid characters."
                ),
                "fix": "invalid-name-",
            }
        ) in check_resource_name("invalid_name-", is_generate_name=True)
