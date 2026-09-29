"""Reading SCIM requests into roster terms (E-21), with the request shapes Entra and Okta send."""

from __future__ import annotations

import pytest

from app.features.roster import domain_scim


def test_a_one_clause_eq_filter_is_read_with_its_canonical_attribute() -> None:
    allowed = domain_scim.USER_FILTERS
    assert domain_scim.parse_filter('userName eq "a@b.com"', allowed=allowed) == ("userName", "a@b.com")
    assert domain_scim.parse_filter('USERNAME EQ "a@b.com"', allowed=allowed) == ("userName", "a@b.com")
    assert domain_scim.parse_filter('emails.value eq "a@b.com"', allowed=allowed) == ("emails", "a@b.com")
    assert domain_scim.parse_filter(None, allowed=allowed) is None


@pytest.mark.parametrize(
    "raw", ['userName co "a"', 'userName eq "a" and active eq true', 'title eq "x"', "userName eq a"]
)
def test_anything_else_is_an_invalid_filter(raw: str) -> None:
    with pytest.raises(domain_scim.InvalidFilter):
        domain_scim.parse_filter(raw, allowed=domain_scim.USER_FILTERS)


def test_a_page_window_is_clamped() -> None:
    assert domain_scim.page_window(None, None) == (0, domain_scim.MAX_PAGE)
    assert domain_scim.page_window(11, 10) == (10, 10)
    assert domain_scim.page_window(1, 10_000) == (0, domain_scim.MAX_PAGE)


def test_entras_string_booleans_and_dotted_names_are_understood() -> None:
    changes = domain_scim.user_patch(
        [
            {"op": "Replace", "path": "active", "value": "False"},
            {"op": "replace", "value": {"name.givenName": "Ana", "name": {"familyName": "Lee"}}},
            {"op": "Add", "path": "title", "value": "Registrar"},
        ]
    )
    assert (changes.active, changes.first_name, changes.last_name) == (False, "Ana", "Lee")


def test_removing_a_name_clears_it() -> None:
    changes = domain_scim.user_patch([{"op": "remove", "path": "name.familyName"}])
    assert changes.clear_last_name and changes.last_name is None


def test_a_malformed_operation_is_refused() -> None:
    with pytest.raises(domain_scim.InvalidPatch):
        domain_scim.user_patch([{"op": "move", "path": "active", "value": True}])
    with pytest.raises(domain_scim.InvalidPatch):
        domain_scim.user_patch([{"op": "replace", "path": "active", "value": "perhaps"}])


def test_group_members_are_added_removed_and_replaced_in_order() -> None:
    changes = domain_scim.group_patch(
        [
            {"op": "Add", "path": "members", "value": [{"value": "c"}, {"value": "a"}]},
            {"op": "Remove", "path": 'members[value eq "b"]'},
            {"op": "Replace", "path": "displayName", "value": "Thursday"},
        ]
    )
    assert changes.display_name == "Thursday"
    assert domain_scim.apply_members(["a", "b"], changes) == ["a", "c"]

    replaced = domain_scim.group_patch([{"op": "replace", "path": "members", "value": [{"value": "z"}]}])
    assert domain_scim.apply_members(["a", "b"], replaced) == ["z"]
