import json
import os
import requests
import shutil

import rocrate_inveniordm.mapping.converter as converter
import rocrate_inveniordm.upload.credentials as credentials


def load_template_rc(file="test/data/template-crate.json"):
    with open(file) as f:
        rc = json.load(f)
    return rc


def set_field_in_template_rde(field, value, rc, rde_id="./"):
    graph = rc.get("@graph")
    for i, entity in enumerate(graph):
        if entity["@id"] == rde_id:
            break

    rc["@graph"][i][field] = value
    return rc, i


def add_entity_to_template(entity, rc):
    rc["@graph"].append(entity)
    return rc


def get_single_mapping(mapping_class, rule):
    m = converter.load_mapping_json()

    if not mapping_class.endswith("_mapping"):
        mapping_class += "_mapping"

    rule = m["$root"][mapping_class]["mappings"][rule]

    return rule


def get_mapping_class(mapping_class):
    m = converter.load_mapping_json()

    if not mapping_class.endswith("_mapping"):
        mapping_class += "_mapping"

    mapping_class = m["$root"][mapping_class]

    return mapping_class


def get_request_headers():
    api_key = credentials.get_api_key()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    return headers


def fetch_inveniordm_record(record_id):
    api_url = credentials.get_repository_base_url()
    r = requests.get(
        f"{api_url}/api/deposit/depositions/{record_id}",
        headers=get_request_headers(),
    )
    r.raise_for_status()
    return r.json()


def zip_crate(crate_path, out_dir, top_folder=False):
    """Zips a crate directory into out_dir, with the crate files at the root of the
    zip, or inside a single top-level folder if top_folder is True.

    :return: Path of the created zip file.
    """
    crate_path = os.path.normpath(crate_path)
    crate_name = os.path.basename(crate_path)
    if top_folder:
        root_dir, base_dir = os.path.dirname(crate_path), crate_name
    else:
        root_dir, base_dir = crate_path, None
    return shutil.make_archive(
        os.path.join(out_dir, crate_name), "zip", root_dir=root_dir, base_dir=base_dir
    )
