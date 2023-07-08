"""Creates / uses MD5 files

Contains the following functions:
    * generate_checksums
    * nest_checksums
    * delete_nested_checksum_files
    * verify_checksums

"""

import os
import unicodedata
from tqdm import tqdm
from natsort import natsorted
from send2trash import send2trash

from utils import (
    concat_filepaths,
    append_unique_lines_to_file,
    index_if_possible,
    make_relative_path,
)
from md5lines import CustomMD5Line
from md5files.md5file_utils import (
    md5,
    get_checksum_save_location,
    extract_from_md5file,
    check_custom_md5file_header,
    separate_by_dirs,
    separate_by_uniqueness,
)
from md5files.md5file_utils import (
    main_checksum_header,
    nested_checksum_header,
    files_to_ignore,
)


def generate_checksums(
    folder_path: str,
    updating_only: bool,
    unsorted_md5_filepath: str = None,
    unsorted_md5_format: str = "md5",
):
    """Creates MD5 checksum file for a folder

    The MD5 checksum file created will contain checksums for all files in the
    folder, including files in nested directories.

    If a file is deleted, its checksum will not be automatically deleted from
    an existing checksum file.

    If a directory contains a nested checksum file, checksums for files in
    that nested file will be used rather than calculating checksums again
    (if needed).

    Args:
        folder_path (str): Path to folder to create MD5 checksum file for.
        updating_only (bool): If true, new files + checksums are added to an
            existing checksum file (if possible). Otherwise, a new checksum
            file will be created (so checksums in an existing file would not
            be used).
        unsorted_md5_filepath (str, optional): If specified, checksums for
            files in `unsorted_md5_filepath` will be used rather than
            calculating checksums again (if needed). Defaults to None.
        unsorted_md5_format (str, optional): Format style of
            `unsorted_md5_filepath`. Ignored if `unsorted_md5_filepath` is not
            specified). Defaults to "md5".

    """
    save_location = get_checksum_save_location(folder_path, updating_only)

    # checksums will only be generated for files not recorded in save_location
    # dirpaths_group = (dirpaths, dirpath_filenames, dirpath_checksums)
    dirpaths_group = _get_dirpaths_group(save_location)

    # unsorted filenames/checksums will be checked before generating checksums for new files
    # unsorted_group = (unsorted_filenames, unsorted_checksums, unsorted_dupe_filenames, unsorted_dupe_checksums)
    unsorted_group = _get_unsorted_group(unsorted_md5_filepath, unsorted_md5_format)

    lines_to_write = [main_checksum_header + "\n"]
    failed_checksums = []

    for root, dirs, files in os.walk(folder_path):
        if not files:
            continue

        root_filtered = make_relative_path(root, os.path.basename(folder_path))

        # get list of filenames that can be skipped in the subdirectory being explored
        existing_filenames = None
        dirpaths_idx = index_if_possible(dirpaths_group[0], root_filtered)
        if dirpaths_idx != -1:
            existing_filenames = dirpaths_group[1][dirpaths_idx]

        # generate checksums and form lines to write
        lines_to_write_part, failed_checksums_part = _generate_checksums_subdir(
            files, root, root_filtered, unsorted_group, existing_filenames
        )

        lines_to_write += lines_to_write_part
        failed_checksums += failed_checksums_part

    append_unique_lines_to_file(save_location, lines_to_write)
    if failed_checksums:
        print("FAILED: due to mismatched checksums from unsorted_md5 source")
    for line in failed_checksums:
        print(f"    {line}")


def _generate_checksums_subdir(
    files: list,
    root: str,
    root_filtered: str,
    unsorted_group: tuple,
    existing_filenames: list = None,
):
    """Part of / Helper for `generate_checksums()`

    Args:
        files (list): List of filenames in subdirectory.
        root (str): Absolute path to subdirectory.
        root_filtered (str): Relative path to subdirectory from main directory.
            being checksummed.
        unsorted_group (tuple[list, list, list, list]): [0] Unique unsorted
            filenames, [1] their corresponding checksums, [2] non-unique
            unsorted filenames, [3] their corresponding checksums.
        existing_filenames (list, optional): Filenames in subdirectory that
            can be skipped. Defaults to None.

    Returns:
        tuple[list, list]: [0] lines_to_write from subdirectory in "custom"
        format, [1] failed_checksums from subdirectory

    """
    # nested filenames/checksums will be checked before generating checksums for new files
    nested_filenames, nested_checksums = [], []
    if ".nested_checksum.txt" in files:
        nested_filenames, nested_checksums = extract_from_md5file(
            concat_filepaths(root, ".nested_checksum.txt"), "custom_nested"
        )

    # unsorted filenames/checksums will be checked before generating checksums for new files
    (
        unsorted_filenames,
        unsorted_checksums,
        unsorted_dupe_filenames,
        unsorted_dupe_checksums,
    ) = unsorted_group

    lines_to_write, failed_checksums = [], []

    for file in tqdm(natsorted(files), leave=False, desc=f"{os.path.basename(root)}"):
        file = unicodedata.normalize("NFC", file)

        if file in files_to_ignore:
            continue

        if existing_filenames != None and file in existing_filenames:
            continue

        # if possible, get md5 checksum of file from alternative source, else calculate checksum (expensive)
        if file in nested_filenames:
            checksum = nested_checksums[nested_filenames.index(file)]
        elif file in unsorted_filenames:
            checksum = unsorted_checksums[unsorted_filenames.index(file)]
        elif file in unsorted_dupe_filenames:
            tqdm.write(f"verifing checksum '{file}' - ({root_filtered})")
            checksum = md5(root + "/" + file)

            matching_filenames = [unsorted_dupe_filenames[idx] for idx, x in enumerate(unsorted_dupe_checksums) if x == checksum]
            if file not in matching_filenames:
                failed_checksums.append(f"'{file}' - ({root_filtered})")
                tqdm.write(f"failed: verifing checksum '{file}'")
                continue

            tqdm.write(f"finished verifing checksum '{file}' - ({root_filtered})")
        else:
            tqdm.write(f"checksumming '{file}' - ({root_filtered})")
            checksum = md5(root + "/" + file)

        # add custom md5 line to lines to write
        line_path = concat_filepaths(root_filtered, file)
        line = CustomMD5Line.get_custom_md5line_string(line_path, checksum) + "\n"
        lines_to_write.append(line)

    return lines_to_write, failed_checksums


def _get_dirpaths_group(save_location: str):
    """Part of / Helper for `generate_checksums()`

    If `save_location` does not exist, return tuple of empty arrays
    Else return dirpaths_group (= dirpaths, dirpath_filenames,
        dirpath_checksums)

    Returns:
        tuple[list, list, list]: [0] dirpaths, [1] dirpath_filenames,
            [2] dirpath_checksums

    """
    if os.path.exists(save_location):
        return separate_by_dirs(*extract_from_md5file(save_location, "custom"))

    return [], [], []


def _get_unsorted_group(unsorted_md5_filepath: str, unsorted_md5_format: str):
    """Part of / Helper for `generate_checksums()`

    If `unsorted_md5_filepath` was not specified, return tuple of empty arrays
    Else return unsorted_group (= unsorted_filenames, unsorted_checksums,
        unsorted_dupe_filenames, unsorted_dupe_checksums)

    Returns:
        tuple[list, list, list, list]: [0] unsorted_filenames,
            [1] unsorted_checksums, [2] unsorted_dupe_filenames,
            [3] unsorted_dupe_checksums

    """
    if unsorted_md5_filepath is None:
        return [], [], [], []

    unsorted_filepaths, unsorted_checksums = extract_from_md5file(
        unsorted_md5_filepath, unsorted_md5_format
    )
    unsorted_filenames = [os.path.basename(file) for file in unsorted_filepaths]

    return separate_by_uniqueness(unsorted_filenames, unsorted_checksums)


def nest_checksums(root_folder: str, updating_only: bool):
    """Creates nested checksum files for a directory from a main checksum file

    A nested checksum file is a file within a directory that contains
    checksums for just that single directory, ignoring nested directories
    (which would have their own nested checksum file). Uses custom_md5line
    short format, which allows a directory to be moved whilst keeping its
    saved checksums intact.

    A nested checksum file is named '.nested_checksum.txt' or
    '.nested_checksum_X.txt' (where X is a number), and the first line is a
    header '; nested checksum'.

    Args:
        root_folder (str): Path to folder to create nested checksum files for
        updating_only (bool): If true, new files + checksums are added to an
            existing nested checksum file (if possible). Otherwise, a new
            nested checksum file will be created.

    """
    main_checksum_filepath = get_checksum_save_location(root_folder, True, False)
    filepaths, checksums = extract_from_md5file(main_checksum_filepath, "custom")

    # paths of sub directories (that contains files) in main checksum file
    unique_dirpaths = []
    # contains an array for each filepath in unique_dirpaths, containing lines to write
    file_contents = []

    for filepath, checksum in zip(filepaths, checksums):
        line_dirpath = os.path.dirname(filepath)

        shortened_formatted_line = (
            CustomMD5Line.get_short_custom_md5line_string(filepath, checksum) + "\n"
        )

        if line_dirpath not in unique_dirpaths:
            unique_dirpaths.append(line_dirpath)
            file_contents.append(
                [nested_checksum_header + "\n", shortened_formatted_line]
            )
        else:
            x = unique_dirpaths.index(line_dirpath)
            if shortened_formatted_line not in file_contents[x]:
                file_contents[x].append(shortened_formatted_line)

    for line_dirpath, lines in zip(unique_dirpaths, file_contents):
        filepath = get_checksum_save_location(
            concat_filepaths(root_folder, line_dirpath), updating_only, True
        )
        append_unique_lines_to_file(filepath, lines)


def delete_nested_checksum_files(root_folder: str):
    """Deletes all nested checksum files within `root_folder`

    A nested checksum file is a file within a directory that contains
    checksums for just that single directory, ignoring nested directories
    (which would have their own nested checksum file). Uses custom_md5line
    short format.

    A nested checksum file is named '.nested_checksum.txt' or
    '.nested_checksum_X.txt' (where X is a number), and the first line is a
    header '; nested checksum'.

    Args:
        root_folder (str): Path to folder in which all nested checksum files
            will be deleted.

    """
    # TODO: add option to output mismatched_headers
    mismatched_headers = []

    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file == ".nested_checksum.txt":
                if check_custom_md5file_header(concat_filepaths(root, file), True):
                    send2trash(concat_filepaths(root, file))
                else:  # filename matches, but header does not
                    mismatched_headers.append(concat_filepaths(root, file))


def verify_checksums(
    folder_path: str,
    use_nested_checksums: bool = False,
    follow_nested_dirs: bool = True,
):
    """Verify integrity of files by comparing to their saved checksums

    If a file does not have a saved checksum, it cannot be verified (skipped).

    Args:
        folder_path (str): Path to folder to verify
        use_nested_checksums (bool, optional): If true, uses checksums in
            nested checksum files. Otherwise, uses main checksum file in
            `folder_path`. Defaults to False.
        follow_nested_dirs (bool, optional): If true, verifies nested
            directories too. Otherwise, only verifies files in the top level
            of directory. Defaults to True.

    """
    if not use_nested_checksums:
        save_location = get_checksum_save_location(folder_path, True)

        if not os.path.exists(save_location):
            print(
                "No checksums were found. Use 'generate_checksums()' to calculate and save new checksums."
            )
            return

        checksummed_filepaths, saved_checksums = extract_from_md5file(
            save_location, "custom"
        )

    # TODO: add option to output passed, failed, new_files
    passed, failed, new_files = [], [], []

    for depth, (root, dirs, files) in enumerate(os.walk(folder_path)):
        if not follow_nested_dirs and depth > 0:
            break

        if not files:
            continue

        root_filtered = unicodedata.normalize(
            "NFC", root.replace(folder_path, "./").replace("\\", "/").replace("//", "/")
        )

        if use_nested_checksums:
            # get path to nested checksum file, skip whole dir if it does not exist
            save_location = get_checksum_save_location(root, True, True)
            if not os.path.exists(save_location):
                print(f"Could not find nested checksum file. Skipping '{root}'")
                continue

            # convert filenames to filepaths relative to folder_path to avoid collisions
            _filenames, saved_checksums = extract_from_md5file(
                save_location, "custom_nested"
            )
            checksummed_filepaths = [f"{root_filtered}/{file}" for file in _filenames]

        # verify checksum (if possible) of each file in this directory
        for file in tqdm(
            natsorted(files), leave=False, desc=f"{os.path.basename(root)}"
        ):
            file = unicodedata.normalize("NFC", file)
            relative_filepath = f"{root_filtered}/{file}"

            if file == ".main_checksum.txt" or file == ".nested_checksum.txt":
                continue

            if (
                relative_filepath not in checksummed_filepaths
            ):  # file has no saved checksum, skip
                new_files.append(relative_filepath)
                tqdm.write(f"NEW FILE, nothing to check against: '{relative_filepath}'")
                continue

            checksum = md5(root + "/" + file)

            if (
                checksum.upper()
                != saved_checksums[
                    checksummed_filepaths.index(relative_filepath)
                ].upper()
            ):
                failed.append(relative_filepath)
                tqdm.write(f"FAILED: '{relative_filepath}'")
            else:  # checksums match, file verified
                passed.append(relative_filepath)
