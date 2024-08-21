import json
import hashlib
import os
import pytest
import pathlib
import re
import requests
import shutil
from subprocess import check_output, CalledProcessError, STDOUT

from test.unit.utils import get_request_headers, fetch_inveniordm_record

CRATES = ["minimal-ro-crate", "test-ro-crate", "real-world-example", "utf-8-csv-crate"]
TEST_DATA_FOLDER = "test/data"
TEST_OUTPUT_FOLDER = "test/output"


@pytest.fixture(scope="module", autouse=True)
def create_output_dir():
    """Creates folder for test outputs."""
    return os.makedirs(TEST_OUTPUT_FOLDER, exist_ok=True)


@pytest.mark.parametrize("crate_name", [*CRATES])
def test_created_datacite_files(crate_name):
    # Arrange
    crate_path = os.path.join(TEST_DATA_FOLDER, crate_name)
    compare_path = os.path.join(TEST_DATA_FOLDER, f"datacite-out-{crate_name}.json")
    with open(compare_path) as expected:
        expected_json = json.load(expected)
    output_file = "datacite-out.json"

    # Act
    try:
        # note - check_output raises CalledProcessError if exit code is non-zero
        # --no-upload prevents upload and generates DataCite files only
        log = check_output(
            f"rocrate_inveniordm {crate_path} --no-upload",
            shell=True,
            text=True,
            stderr=STDOUT,
        )
    except CalledProcessError as e:
        log = e.output
    finally:
        # always preserve log in TEST_OUTPUT_FOLDER
        with open(
            os.path.join(TEST_OUTPUT_FOLDER, f"log-datacite-{crate_name}.txt"),
            "w",
        ) as log_file:
            log_file.write(log)
    # if successful, preserve DataCite output
    shutil.copyfile(
        output_file, os.path.join(TEST_OUTPUT_FOLDER, f"datacite-out-{crate_name}.json")
    )

    # Assert
    assert "Created datacite-out.json, skipping upload" in log
    assert os.path.exists(output_file)
    with open(output_file) as output:
        output_json = json.load(output)
        assert output_json == expected_json


@pytest.mark.parametrize("crate_name", [*CRATES])
def test_created_invenio_records(crate_name):
    # Arrange
    crate_path = os.path.join(TEST_DATA_FOLDER, crate_name)
    compare_path = os.path.join(TEST_DATA_FOLDER, f"datacite-out-{crate_name}.json")
    with open(compare_path) as expected:
        expected_json = json.load(expected)
        expected_metadata = expected_json["metadata"]
    expected_log_pattern = r"^Successfully created record (?P<id>[0-9]*)$"

    # Act
    try:
        # note - check_output raises CalledProcessError if exit code is non-zero
        log = check_output(
            f"rocrate_inveniordm {crate_path}", shell=True, text=True, stderr=STDOUT
        )
    except CalledProcessError as e:
        log = e.output
    finally:
        with open(
            os.path.join(TEST_OUTPUT_FOLDER, f"log-upload-{crate_name}.txt"),
            "w",
        ) as log_file:
            log_file.write(log)
    match = re.search(expected_log_pattern, log, flags=re.MULTILINE)
    record_id = match.group("id")

    headers = get_request_headers()
    record = fetch_inveniordm_record(record_id)
    metadata = record["metadata"]

    # Assert
    assert metadata["title"] == expected_metadata["title"]
    assert metadata["upload_type"] == expected_metadata["resource_type"]["id"]
    assert metadata["access_right"] == "open"
    assert len(metadata["creators"]) == len(expected_metadata["creators"])
    if "contributors" in expected_metadata:
        assert len(metadata["contributors"]) == len(expected_metadata["contributors"])
    else:
        assert "contributors" not in metadata

    # check rights
    if "rights" in expected_metadata:
        assert metadata["rights"][0]["title"] == expected_metadata["rights"][0]["title"]
        assert (
            metadata["rights"][0]["description"]
            == expected_metadata["rights"][0]["description"]
        )
        assert (
            metadata["rights"][0]["description"]
            == expected_metadata["rights"][0]["link"]
        )

    # check files
    if expected_json["files"]["enabled"]:
        assert len(record["files"]) != 0
        for file in record["files"]:
            filename = file["filename"]
            local_path = next(
                pathlib.Path(os.path.join(TEST_DATA_FOLDER, crate_name)).glob(
                    f"**/{filename}"
                )
            )
            with open(local_path) as local_file:
                remote_file_data = requests.get(
                    file["links"]["download"], headers=headers
                ).content
                assert local_file.read() == remote_file_data.decode()
    else:
        assert len(record["files"]) == 0
    assert record["state"] == "unsubmitted"
    assert record["submitted"] is False


def test_license_found_from_spdx_id():
    # Arrange
    crate_name = "test-crate-spdx-license"
    crate_path = os.path.join(TEST_DATA_FOLDER, crate_name)
    expected_log_pattern = r"^Successfully created record (?P<id>[0-9]*)$"

    # Act
    try:
        # note - check_output raises CalledProcessError if exit code is non-zero
        log = check_output(
            f"rocrate_inveniordm {crate_path}", shell=True, text=True, stderr=STDOUT
        )
    except CalledProcessError as e:
        log = e.output
    finally:
        with open(
            os.path.join(TEST_OUTPUT_FOLDER, f"log-upload-{crate_name}.txt"),
            "w",
        ) as log_file:
            log_file.write(log)
    match = re.search(expected_log_pattern, log, flags=re.MULTILINE)
    record_id = match.group("id")

    record = fetch_inveniordm_record(record_id)
    metadata = record["metadata"]

    print(metadata)

    # Assert
    assert "rights" in metadata
    assert metadata["rights"][0]["title"] == "CC BY-NC-SA 4.0 International"
    assert (
        metadata["rights"][0]["description"]
        == "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International"
    )
    assert metadata["rights"][0]["id"] == "cc-by-nc-sa-4.0"

    assert metadata["rights"][0]["link"] == "https://spdx.org/licenses/CC-BY-NC-SA-4.0"


def test_cli__zip():
    """Test uploading RO-Crate as a single zip file."""
    # Arrange
    crate_name = "test-ro-crate"
    crate_path = os.path.join(TEST_DATA_FOLDER, crate_name)
    expected_log_pattern_1 = "Creating zipped crate"
    expected_log_pattern_2 = r"^Successfully created record (?P<id>[0-9]*)$"

    # Act
    # note - check_output raises CalledProcessError if exit code is non-zero
    log = check_output(
        f"rocrate_inveniordm {crate_path} -z", shell=True, text=True, stderr=STDOUT
    )
    match = re.search(expected_log_pattern_2, log, flags=re.MULTILINE)
    record_id = match.group("id")
    shutil.copyfile(
        f"{crate_name}.zip", os.path.join(TEST_OUTPUT_FOLDER, f"{crate_name}.zip")
    )

    record = fetch_inveniordm_record(record_id)

    # Assert
    assert expected_log_pattern_1 in log
    assert len(record["files"]) == 1
    # check filename
    result_zip = record["files"][0]
    assert result_zip["filename"] == f"{crate_name}.zip"
    # check MD5 checksum
    with open(f"{crate_name}.zip", "rb") as local_file:
        local_checksum = hashlib.md5(local_file.read()).hexdigest()
    assert result_zip["checksum"] == local_checksum


def test_cli__datacite():
    """Test creating a record from a pre-existing DataCite file."""
    # Arrange
    crate_name = "test-ro-crate"
    crate_path = os.path.join(TEST_DATA_FOLDER, crate_name)
    compare_path = os.path.join(TEST_DATA_FOLDER, f"datacite-out-{crate_name}.json")
    with open(compare_path) as expected:
        expected_json = json.load(expected)
        expected_metadata = expected_json["metadata"]
    expected_log_pattern_1 = "Skipping metadata conversion, loading DataCite file"
    expected_log_pattern_2 = r"^Successfully created record (?P<id>[0-9]*)$"

    # Act
    # note - check_output raises CalledProcessError if exit code is non-zero
    log = check_output(
        f"rocrate_inveniordm {crate_path} -d {compare_path}",
        shell=True,
        text=True,
        stderr=STDOUT,
    )
    match = re.search(expected_log_pattern_2, log, flags=re.MULTILINE)
    record_id = match.group("id")

    record = fetch_inveniordm_record(record_id)
    metadata = record["metadata"]

    # Assert
    assert expected_log_pattern_1 in log
    # check one piece of metadata to confirm it was uploaded
    assert metadata["title"] == expected_metadata["title"]
    # check submission state
    assert record["state"] == "unsubmitted"
    assert record["submitted"] is False


def test_cli__omit_roc_files():
    """Test creating a record with omit_roc_files option."""
    # Arrange
    crate_name = "test-ro-crate"
    crate_path = os.path.join(TEST_DATA_FOLDER, crate_name)
    expected_log_pattern = r"^Successfully created record (?P<id>[0-9]*)$"

    # Act
    # note - check_output raises CalledProcessError if exit code is non-zero
    log = check_output(
        f"rocrate_inveniordm {crate_path} -o", shell=True, text=True, stderr=STDOUT
    )
    match = re.search(expected_log_pattern, log, flags=re.MULTILINE)
    record_id = match.group("id")

    record = fetch_inveniordm_record(record_id)

    # Assert
    for file in record["files"]:
        filename = file["filename"]
        assert filename != "ro-crate-metadata.json"
        local_path = next(
            pathlib.Path(os.path.join(TEST_DATA_FOLDER, crate_name)).glob(
                f"**/{filename}"
            )
        )
        assert "ro-crate-preview" not in str(local_path.relative_to(crate_path))


def test_cli__publish():
    """Test creating a record with publish option."""
    # Arrange
    crate_name = "test-ro-crate"
    crate_path = os.path.join(TEST_DATA_FOLDER, crate_name)
    expected_log_pattern = r"^Successfully created record (?P<id>[0-9]*)$"

    # Act
    # note - check_output raises CalledProcessError if exit code is non-zero
    log = check_output(
        f"rocrate_inveniordm {crate_path} -p", shell=True, text=True, stderr=STDOUT
    )
    match = re.search(expected_log_pattern, log, flags=re.MULTILINE)
    record_id = match.group("id")

    record = fetch_inveniordm_record(record_id)

    # Assert
    assert record["state"] == "done"
    assert record["submitted"] is True
