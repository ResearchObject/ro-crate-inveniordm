from test.unit.utils import (
    add_entity_to_template,
    get_single_mapping,
    load_template_rc,
    set_field_in_template_rde,
)

import pytest

from rocrate_inveniordm.mapping.converter import (
    apply_mapping,
    get_mapping_paths,
    setup_dc,
)

license_string_uri = "https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode"
license_string_title = "CC BY-NC-SA 4.0 International"
license_string_spdx = "https://spdx.org/licenses/CC-BY-NC-SA-4.0"
license_entity = {
    "@id": "https://spdx.org/licenses/CC-BY-NC-SA-4.0",
    "@type": "CreativeWork",
    "name": "CC BY-NC-SA 4.0 International",
    "description": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International",
    "identifier": "https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode",
}


def test_rights_string__uri():
    rc = load_template_rc()
    rc, _ = set_field_in_template_rde("license", license_string_uri, rc)
    rule_name = "rights_link_mapping_uri_direct"
    rule = get_single_mapping("rights", rule_name)
    paths = get_mapping_paths(rc, {rule_name: rule})
    dc = setup_dc()

    dc, _ = apply_mapping(rule, paths, rc, dc)

    print(dc)
    assert dc["metadata"]["rights"][0]["link"] == license_string_uri


def test_rights_string__title():
    rc = load_template_rc()
    rc, _ = set_field_in_template_rde("license", license_string_title, rc)
    rule_name = "rights_link_mapping_title_direct"
    rule = get_single_mapping("rights", rule_name)
    paths = get_mapping_paths(rc, {rule_name: rule})
    dc = setup_dc()

    dc, _ = apply_mapping(rule, paths, rc, dc)

    assert dc["metadata"]["rights"][0]["title"] == license_string_title


def test_rights_string__spdx():
    rc = load_template_rc()
    rc, _ = set_field_in_template_rde("license", license_string_spdx, rc)
    rule_name = "rights_link_mapping_spdx_id_direct"
    rule = get_single_mapping("rights", rule_name)
    paths = get_mapping_paths(rc, {rule_name: rule})
    dc = setup_dc()

    dc, _ = apply_mapping(rule, paths, rc, dc)

    assert dc["metadata"]["rights"][0]["id"] == "cc-by-nc-sa-4.0"


@pytest.mark.parametrize(
    ["rule_name", "field", "expected"],
    [
        ("rights_title_mapping", "title", {"en": license_entity["name"]}),
        (
            "rights_description_mapping",
            "description",
            {"en": license_entity["description"]},
        ),
        ("rights_link_mapping", "link", license_entity["identifier"]),
    ],
)
def test_rights_entity(rule_name, field, expected):
    rc = load_template_rc()
    rc = add_entity_to_template(license_entity, rc)
    rc, _ = set_field_in_template_rde("license", {"@id": license_entity["@id"]}, rc)
    dc = setup_dc()
    rule = get_single_mapping("rights", rule_name)
    paths = get_mapping_paths(rc, {rule_name: rule})

    dc, _ = apply_mapping(rule, paths, rc, dc)

    assert dc["metadata"]["rights"][0][field] == expected
