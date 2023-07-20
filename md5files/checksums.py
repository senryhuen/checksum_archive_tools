"""Creates / uses MD5 files

Contains the following functions:
    * generate_checksums
    * nest_checksums
    * delete_nested_checksum_files
    * verify_checksums
    * remove_missing_checksums

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
    is_checksum_filename,
    finding_missing_files,
    remove_checksums,
)
from md5files.md5file_utils import (
    NESTED_CHECKSUM_FILENAME,
    MAIN_CHECKSUM_HEADER,
    NESTED_CHECKSUM_HEADER,
)


def generate_checksums(
    folder_path: str,
    updating_only: bool,
    unsorted_md5_filepath: str = None,
    unsorted_md5_format: str = "md5",
    files_to_ignore: list = None,
    files_to_ignore_filepath: str = None,
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
        files_to_ignore (list, optional): List containing filenames (including
            extensions) to ignore when checksumming. Any file that matches a
            filename in the list will be skipped and not checksummed. Defaults
            to None.
        files_to_ignore_filepath (str, optional): Path to file containing
            filenames (including extensions) to ignore when checksumming. Any
            file that matches a filename in the file will be skipped and not
            checksummed. Defaults to None.

    """
    save_location = get_checksum_save_location(folder_path, updating_only)

    # checksums will only be generated for files not recorded in save_location
    # dirpaths_group = (dirpaths, dirpath_filenames, dirpath_checksums)
    dirpaths_group = _get_dirpaths_group(save_location)

    # unsorted filenames/checksums will be checked before generating checksums for new files
    # unsorted_group = (unsorted_filenames, unsorted_checksums, unsorted_dupe_filenames, unsorted_dupe_checksums)
    unsorted_group = _get_unsorted_group(unsorted_md5_filepath, unsorted_md5_format)

    # list of filenames to ignore when checksumming
    if not files_to_ignore:
        files_to_ignore = []

    if files_to_ignore_filepath:
        with open(files_to_ignore_filepath, "r", encoding="utf8") as file:
            files_to_ignore += [line.rstrip() for line in file.readlines()]

    lines_to_write = [MAIN_CHECKSUM_HEADER + "\n"]
    failed_checksums = []

    for root, _, files in os.walk(folder_path):
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
            files,
            root,
            root_filtered,
            unsorted_group,
            existing_filenames,
            files_to_ignore,
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
    files_to_ignore: list = None,
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
        files_to_ignore (list, optional): List containing filenames (including
            extensions) to ignore when checksumming. Any file that matches a
            filename in the list will be skipped and not checksummed. Defaults
            to None.

    Returns:
        tuple[list, list]: [0] lines_to_write from subdirectory in "custom"
        format, [1] failed_checksums from subdirectory

    """
    # list of filenames to ignore when checksumming
    if not files_to_ignore:
        files_to_ignore = []

    # nested filenames/checksums will be checked before generating checksums for new files
    nested_filenames, nested_checksums = [], []
    if NESTED_CHECKSUM_FILENAME in files:
        nested_filenames, nested_checksums = extract_from_md5file(
            concat_filepaths(root, NESTED_CHECKSUM_FILENAME), "custom_nested"
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

        if file in files_to_ignore or is_checksum_filename(file):
            continue

        if existing_filenames is not None and file in existing_filenames:
            continue

        # if possible, get md5 checksum of file from alternative source, else calculate checksum (expensive)
        if file in nested_filenames:
            checksum = nested_checksums[nested_filenames.index(file)]
        elif file in unsorted_filenames:
            checksum = unsorted_checksums[unsorted_filenames.index(file)]
        elif file in unsorted_dupe_filenames:
            tqdm.write(f"verifing checksum '{file}' - ({root_filtered})")
            checksum = md5(root + "/" + file)

            matching_filenames = [
                unsorted_dupe_filenames[idx]
                for idx, x in enumerate(unsorted_dupe_checksums)
                if x == checksum
            ]
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

    A nested checksum file is named '.nested_checksum.txt' and the first line
    is a header '; nested checksum'.

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
                [NESTED_CHECKSUM_HEADER + "\n", shortened_formatted_line]
            )
        else:
            idx = unique_dirpaths.index(line_dirpath)
            if shortened_formatted_line not in file_contents[idx]:
                file_contents[idx].append(shortened_formatted_line)

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

    A nested checksum file is named '.nested_checksum.txt' and the first line
    is a header '; nested checksum'. Old nested checksum files (renamed to
    '.nested_checksum_old') are not deleted.

    Args:
        root_folder (str): Path to folder in which all nested checksum files
            will be deleted.

    """
    # TODO: add option to output mismatched_headers
    mismatched_headers = []

    for root, _, files in os.walk(root_folder):
        if NESTED_CHECKSUM_FILENAME in files:
            nested_checksum_filepath = concat_filepaths(root, NESTED_CHECKSUM_FILENAME)
            if check_custom_md5file_header(nested_checksum_filepath, True):
                send2trash(nested_checksum_filepath)
            else:  # filename matches, but header does not
                mismatched_headers.append(nested_checksum_filepath)


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

    for depth, (root, _, files) in enumerate(os.walk(folder_path)):
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

            if is_checksum_filename(file):
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


def remove_missing_checksums(
    folder_path: str, save_orig: bool = True, require_confirmation: bool = True
) -> int:
    """Removes lines from "custom" checksum file for non-existant filepaths

    Does not also remove missing checksums from nested checksums. To remove
    from nested checksums, redo them with the updated main checksum file -
    either by using `delete_nested_checksum_files(folder_path)` followed by
    `nest_checksums(folder_path)`, or just
    `nest_checksums(folder_path, updating_only=False)`.

    Args:
        folder_path (str): Path to folder where files were checksummed
            (contains ".main_checksum.txt" and checksum filepaths are relative
            to this folder). This is the location where existence of files
            will be checked.
        save_orig (bool, optional): If True, original checksum file will be
            saved (renamed first), otherwise it will just be overwritten.
            Defaults to True.
        require_confirmation (bool, optional): If True, asks before removing.
            Defaults to True.

    Returns:
        int: number of lines removed

    """
    checksum_filepath = get_checksum_save_location(folder_path, True)

    # if no checksum file found, then return 0 (no lines removed)
    if not os.path.exists(checksum_filepath):
        return 0

    missing_files = finding_missing_files(folder_path, checksum_filepath)
    _, removed_lines = remove_checksums(
        checksum_filepath, missing_files, save_orig, require_confirmation
    )

    return len(removed_lines)
