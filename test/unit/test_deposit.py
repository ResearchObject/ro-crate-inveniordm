import json
import os
import zipfile

import pytest

from rocrate_inveniordm.deposit import (
    METADATA_FILE,
    find_metadata_in_zip,
    get_files_to_upload,
    load_crate_metadata,
)
from test.unit.utils import zip_crate

CRATE_PATH = "test/data/test-ro-crate"


@pytest.fixture
def expected_metadata():
    """Loads the metadata of the test crate."""
    with open(os.path.join(CRATE_PATH, METADATA_FILE)) as f:
        return json.load(f)


def test_load_crate_metadata__directory(expected_metadata):
    # Act
    metadata = load_crate_metadata(CRATE_PATH)

    # Assert
    assert metadata == expected_metadata


def test_load_crate_metadata__zip(expected_metadata, tmp_path):
    # Arrange
    zip_path = zip_crate(CRATE_PATH, tmp_path)

    # Act
    metadata = load_crate_metadata(zip_path)

    # Assert
    assert metadata == expected_metadata


def test_load_crate_metadata__zip_top_folder(expected_metadata, tmp_path):
    # Arrange
    zip_path = zip_crate(CRATE_PATH, tmp_path, top_folder=True)

    # Act
    metadata = load_crate_metadata(zip_path)

    # Assert
    assert metadata == expected_metadata


def test_load_crate_metadata__directory_without_metadata(tmp_path):
    # Act
    with pytest.raises(SystemExit) as e:
        load_crate_metadata(str(tmp_path))

    # Assert
    assert e.value.code == 1


def test_load_crate_metadata__zip_without_metadata(tmp_path):
    # Arrange
    zip_path = tmp_path / "crate.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("data.txt", "not a crate")

    # Act
    with pytest.raises(SystemExit) as e:
        load_crate_metadata(str(zip_path))

    # Assert
    assert e.value.code == 1


def test_load_crate_metadata__not_zip_file(tmp_path):
    # Arrange
    file_path = tmp_path / "crate.txt"
    file_path.write_text("not a crate")

    # Act
    with pytest.raises(SystemExit) as e:
        load_crate_metadata(str(file_path))

    # Assert
    assert e.value.code == 1


def test_find_metadata_in_zip__root():
    # Arrange
    names = [METADATA_FILE, "data/", "data/file.txt"]

    # Act
    result = find_metadata_in_zip(names)

    # Assert
    assert result == METADATA_FILE


def test_find_metadata_in_zip__top_folder_with_macos_files():
    # Arrange
    names = [
        "crate/",
        f"crate/{METADATA_FILE}",
        "__MACOSX/",
        f"__MACOSX/crate/._{METADATA_FILE}",
    ]

    # Act
    result = find_metadata_in_zip(names)

    # Assert
    assert result == f"crate/{METADATA_FILE}"


def test_find_metadata_in_zip__several_top_folders():
    # Arrange
    names = [f"crate1/{METADATA_FILE}", f"crate2/{METADATA_FILE}"]

    # Act
    result = find_metadata_in_zip(names)

    # Assert
    assert result is None


def test_get_files_to_upload__directory():
    # Act
    files = get_files_to_upload(CRATE_PATH)

    # Assert
    assert os.path.join(CRATE_PATH, METADATA_FILE) in files
    assert all(os.path.isfile(file) for file in files)


def test_get_files_to_upload__directory_omit_roc_files():
    # Act
    files = get_files_to_upload(CRATE_PATH, omit_roc_files=True)

    # Assert
    assert len(files) > 0
    assert not any(
        METADATA_FILE in file or "ro-crate-preview" in file for file in files
    )


def test_get_files_to_upload__directory_use_zip(tmp_path, monkeypatch):
    # Arrange
    crate_path = os.path.abspath(CRATE_PATH)
    monkeypatch.chdir(tmp_path)

    # Act
    files = get_files_to_upload(crate_path, use_zip=True)

    # Assert
    assert files == [str(tmp_path / "test-ro-crate.zip")]
    assert zipfile.is_zipfile(files[0])


def test_get_files_to_upload__zip(tmp_path):
    # Arrange
    zip_path = zip_crate(CRATE_PATH, tmp_path)

    # Act
    files = get_files_to_upload(zip_path, use_zip=True)

    # Assert
    assert files == [zip_path]


def test_get_files_to_upload__zip_omit_roc_files(tmp_path):
    # Arrange
    zip_path = zip_crate(CRATE_PATH, tmp_path)

    # Act
    with pytest.raises(SystemExit) as e:
        get_files_to_upload(zip_path, omit_roc_files=True)

    # Assert
    assert e.value.code == 1
