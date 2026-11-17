"""
    This script deposits a RO-Crate directory or zip file to an InvenioRDM repository.

    :author: Philipp Beer
    :author: Milan Szente
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import sys
import zipfile

import rocrate_inveniordm.mapping.converter as converter
import rocrate_inveniordm.upload.uploader as uploader

METADATA_FILE = "ro-crate-metadata.json"


def main():
    """
    CLI entrypoint. Passes CLI arguments to deposit().
    """

    parser = argparse.ArgumentParser(
        description="Takes a RO-Crate directory or zip file as input and uploads it to "
        "an InvenioRDM repository"
    )

    parser.add_argument(
        "ro_crate_directory",
        help="Path to the RO-Crate directory or zip file to upload",
        type=str,
        action="store",
    )
    parser.add_argument(
        "-d",
        "--datacite",
        help="Path to a DataCite metadata file to use for the upload. Skips the "
        "conversion process from RO-Crate metadata to DataCite",
        type=str,
        action="store",
        nargs=1,
    )
    parser.add_argument(
        "--no-upload",
        help="Stop before creating InvenioRDM record and do not upload files. Use this "
        "option to create a DataCite metadata file for manual review",
        action="store_true",
    )
    # included for backwards compatibility
    parser.add_argument(
        "-o",
        "--omit-roc-files",
        help="Omit files named 'ro-crate-metadata.json' and directories/files "
        "containing 'ro-crate-preview' from the upload (not recommended)",
        action="store_true",
    )
    parser.add_argument(
        "-p",
        "--publish",
        help="Publish the record after uploading",
        action="store_true",
    )
    parser.add_argument(
        "-z",
        "--zip",
        help="Instead of uploading all the files within the crate, create and upload a "
        "single zip file containing the whole crate (not needed for a zipped crate, "
        "which is always uploaded as is)",
        action="store_true",
    )
    args = parser.parse_args()

    crate_dir = args.ro_crate_directory
    datacite_list = args.datacite
    no_upload = args.no_upload
    omit_roc_files = args.omit_roc_files
    publish = args.publish
    use_zip = args.zip

    datacite_file = datacite_list[0] if datacite_list else None

    deposit(
        ro_crate_dir=crate_dir,
        datacite_file=datacite_file,
        no_upload=no_upload,
        omit_roc_files=omit_roc_files,
        publish=publish,
        use_zip=use_zip,
    )


def deposit(
    ro_crate_dir: str,
    datacite_file: str | None = None,
    no_upload: bool = False,
    omit_roc_files: bool = False,
    publish: bool = False,
    use_zip: bool = False,
):
    """
    The main function of the script.
    It takes a RO-Crate directory or zip file as input and uploads it to an InvenioRDM
    repository.

    :param ro_crate_dir: Path to the RO-Crate directory or zip file to upload. A zip
        file is uploaded as is.
    :param datacite_file: Path to a DataCite metadata file which should be used for the
        upload. Skips the conversion process from RO-Crate metadata to DataCite.
        Defaults to None
    :param no_upload: Stop before creating InvenioRDM record and do not upload files.
        Use this option to create a DataCite metadata file for manual review. Defaults
        to False
    :param omit_roc_files: Omit files named 'ro-crate-metadata.json' and
        directories/files containing 'ro-crate-preview' from the upload (not
        recommended). Defaults to False
    :param publish: Publish the record after uploading. Defaults to False
    :param zip: Instead of uploading all the files within the crate, create and upload a
        single zip file containing the whole crate. Defaults to False
    :return: The ID of the created record, or None if no record was created.
    """

    ro_crate_metadata = load_crate_metadata(ro_crate_dir)
    all_files = get_files_to_upload(ro_crate_dir, omit_roc_files, use_zip)

    if datacite_file:
        # skip conversion and use the provided file
        print(f"Skipping metadata conversion, loading DataCite file {datacite_file}")
        with open(datacite_file, "r") as f:
            data_cite_metadata = json.load(f)
    else:
        # if no files to upload, just set the metadata on the record
        metadata_only = False
        if len(all_files) == 0:
            metadata_only = True

        # Convert Metadata
        data_cite_metadata = converter.convert(
            ro_crate_metadata, metadata_only=metadata_only
        )
        # store datacite metadata
        with open("datacite-out.json", "w") as f:
            json.dump(data_cite_metadata, f, indent=4)

    # Upload and publish files, depending on no_upload and publish options
    if no_upload:
        print("Created datacite-out.json, skipping upload.")
        return None
    else:
        record_id = uploader.deposit(data_cite_metadata, all_files, publish=publish)

        print(f"Successfully created record {record_id}")
        return record_id


def load_crate_metadata(crate_path: str) -> dict:
    """
    Loads the RO-Crate metadata from a RO-Crate directory or zip file.
    Exits the program if the metadata file is not found.

    :param crate_path: Path to the RO-Crate directory or zip file.
    :return: Dictionary containing the RO-Crate metadata.
    """
    if os.path.isdir(crate_path):
        metadata_file = os.path.join(crate_path, METADATA_FILE)
        if os.path.isfile(metadata_file):
            with open(metadata_file, "r") as f:
                return json.load(f)
    elif zipfile.is_zipfile(crate_path):
        with zipfile.ZipFile(crate_path) as zf:
            metadata_name = find_metadata_in_zip(zf.namelist())
            if metadata_name:
                with zf.open(metadata_name) as f:
                    return json.load(f)

    print(
        f"'{crate_path}' is not a RO-Crate directory or zip file: "
        f"'{METADATA_FILE}' not found."
    )
    sys.exit(1)


def find_metadata_in_zip(names: list[str]) -> str | None:
    """
    Finds the RO-Crate metadata file in a zip file, either at the root or inside a
    single top-level directory.

    :param names: Names of all the entries in the zip file.
    :return: The entry name of the metadata file, or None if not found.
    """
    if METADATA_FILE in names:
        return METADATA_FILE
    # ignore the folder of resource forks that macOS adds when compressing
    top_dirs = {name.split("/")[0] for name in names if not name.startswith("__MACOSX")}
    if len(top_dirs) == 1:
        candidate = f"{top_dirs.pop()}/{METADATA_FILE}"
        if candidate in names:
            return candidate
    return None


def get_files_to_upload(
    crate_path: str, omit_roc_files: bool = False, use_zip: bool = False
) -> list[str]:
    """
    Lists the files to upload for a RO-Crate directory or zip file.
    Exits the program if omit_roc_files is used with a zip file.

    :param crate_path: Path to the RO-Crate directory or zip file.
    :param omit_roc_files: Omit files named 'ro-crate-metadata.json' and
        directories/files containing 'ro-crate-preview'. Defaults to False
    :param use_zip: Create and return a single zip file containing the whole crate.
        Defaults to False
    :return: List of paths of the files to upload.
    """
    if os.path.isfile(crate_path):
        # a zipped crate is uploaded as is
        if omit_roc_files:
            print("The --omit-roc-files option cannot be used with a zipped crate.")
            sys.exit(1)
        return [crate_path]

    if use_zip:
        crate_name = os.path.basename(crate_path.strip("/"))
        print(f"Creating zipped crate {crate_name}.zip")
        return [shutil.make_archive(crate_name, "zip", root_dir=crate_path)]

    # Exclude RO-Crate metadata, and RO-Crate website files if requested
    all_files = []
    for file in glob.glob(f"{crate_path}/**", recursive=True):
        if omit_roc_files and ("ro-crate-preview" in file or METADATA_FILE in file):
            continue
        if os.path.isfile(file):
            all_files.append(file)
    return all_files


if __name__ == "__main__":
    main()
