"""Utilities for MD5 files

Contains the following functions:
    * is_checksum_filename
    * get_checksum_save_location
    * check_custom_md5file_header
    * extract_from_md5line
    * extract_from_md5file
    * md5
    * revert_md5file_to_teracopy
    * find_missing_files
    * remove_checksums
    * separate_by_dirs
    * separate_by_uniqueness

"""

import os, re
import hashlib
import unicodedata

from utils import (
    clean_filepath,
    index_if_possible,
    concat_filepaths,
    append_unique_lines_to_file,
)
from md5lines import MD5Line, TeracopyMD5Line, CustomMD5Line

nested_checksum_filename = ".nested_checksum.txt"
main_checksum_filename = ".main_checksum.txt"

nested_checksum_header = "; nested_checksum"
main_checksum_header = "; main_checksum"

accepted_format_types = ["md5", "custom", "custom_nested", "teracopy"]


def is_checksum_filename(s: str, checksum_type: str = None) -> bool:
    """Checks if filename is for a main/nested checksum file

    Args:
        s (str): filename including extension
        checksum_type (str, optional): Match to checksum filenames of
            checksum_type. If None, will match to any type. Accepted values:
            "custom" or "custom_nested". If value not recognised, will default
            to None. Defaults to None.

    Returns:
        bool: returns True if `s` is a filename for a checksum file of
            `checksum_type`, False otherwise

    """
    if checksum_type == "custom_nested":
        return s == nested_checksum_filename
    elif checksum_type == "custom":
        return s == main_checksum_filename

    return s == main_checksum_filename or s == nested_checksum_filename


def get_checksum_save_location(
    folder: str, updating_only: bool, nested: bool = False
) -> str:
    """Gets filepath to a custom MD5 checksum file

    The filename of the filepath will be ".nested_checksum.txt" if nested, or
    ".main_checksum.txt" otherwise.

    Args:
        folder (str): Path to directory that custom MD5 checksum file is for.
        updating_only (str): If true, will return path to checksum file even if
            it already exists. If false, an existing file would be renamed first.
        nested (bool, optional): If true, the filename will indicate a nested
            file. If false, it will indicate a main checksum file. Defaults to
            False.

    Returns:
        str: save location for custom MD5 file, which is a filepath to a file
            (that may not exist) in `folder`

    """
    # folder path must not have trailing slash - remove if necessary
    folder = clean_filepath(folder, False)

    save_location = f"{folder}/{main_checksum_filename}"
    if nested:
        save_location = f"{folder}/{nested_checksum_filename}"

    if os.path.exists(save_location):
        # if save_location exists, check header is correct
        if not check_custom_md5file_header(save_location, nested):
            format_type = "custom_nested" if nested else "custom"
            raise ValueError(
                f"'{save_location}' does not contain header for format_type '{format_type}'"
            )

        # if not updating_only, rename existing file at save_location
        if not updating_only:
            save_location_split = os.path.splitext(save_location)
            old_save_location = f"{save_location_split[0]}_old{save_location_split[1]}"
            old_save_location_template = (
                save_location_split[0] + "_old ({})" + save_location_split[1]
            )

            # iterate count until filename does not exist
            count = 1
            while os.path.exists(old_save_location):
                old_save_location = old_save_location_template.format(count)
                count += 1

            os.rename(save_location, old_save_location)

    return save_location


def check_custom_md5file_header(filepath: str, nested: bool) -> bool:
    """Checks file at `filepath` contains correct header

    Nested checksum file header is '; nested checksum'.
    Main checksum file header is '; main checksum'.

    Args:
        filepath (str): Path to file to check header for
        nested (bool): If true, expects a nested checksum file header.
            Otherwise expects a main checksum file header.

    Returns:
        bool: True if file at `filepath` contains expected header, False otherwise

    """
    with open(filepath, "r", encoding="utf-8") as file:
        header = file.readline().replace("\n", "")

    correct_header = nested_checksum_header if nested else main_checksum_header

    if header != correct_header:
        return False

    return True


def extract_from_md5line(md5_line: str, format_type: str = "md5") -> tuple[str, str]:
    """Gets filepath and checksum from a MD5 checksum line

    Args:
        md5_line (str): Line in a format from a MD5 checksum file.
        format_type (str, optional): Format style of `md5_line`. Accepted
            values: "md5", "custom", "custom_nested", "teracopy". Defaults to
            "md5".

    Raises:
        ValueError: Invalid `format_type` (must be one of accepted values)

    Returns:
        tuple[str, str]: [filepath, checksum] extracted from `md5_line`

    """
    # validates format_type arg
    if format_type.lower() not in accepted_format_types:
        raise ValueError(f"format_type: invalid type: '{format_type}'")

    md5_line = unicodedata.normalize("NFC", md5_line)

    # decide which implementation of extract_filepath/extract_checksum method to use
    format_type = format_type.lower()
    if format_type == "md5":
        return MD5Line.extract_filepath(md5_line), MD5Line.extract_checksum(md5_line)
    elif format_type == "custom" or format_type == "custom_nested":
        return CustomMD5Line.extract_filepath(md5_line), CustomMD5Line.extract_checksum(
            md5_line
        )
    elif format_type == "teracopy":
        return TeracopyMD5Line.extract_filepath(
            md5_line
        ), TeracopyMD5Line.extract_checksum(md5_line)


def extract_from_md5file(
    md5_filepath: str, format_type: str = "md5"
) -> tuple[list, list]:
    """Gets filepaths and checksums from a MD5 checksum file

    Args:
        md5_filepath (str): Path to file containing filepaths and checksums.
        format_type (str, optional): Format style of `md5_filepath`. Accepted
            values: "md5", "custom", "custom_nested", "teracopy". Defaults to
            "md5".

    Raises:
        ValueError: Invalid `format_type` (must be one of accepted values)
        ValueError: `md5_filepath` does not contain expected header

    Returns:
        tuple[list, list]: a list of filepaths (first list in tuple) and a
            list of checksums in corresponding order to filepaths (second list
            in tuple)

    """
    # validates format_type arg
    if format_type.lower() not in accepted_format_types:
        raise ValueError(f"format_type: invalid type: '{format_type}'")

    # validates md5_filepath arg
    with open(md5_filepath, "r", encoding="utf-8") as md5_file:
        md5_lines = md5_file.readlines()

    # decide which version of overridden extract_filepath/extract_checksum method to use
    if format_type == "md5":
        extract_filepath = MD5Line.extract_filepath
        extract_checksum = MD5Line.extract_checksum
    elif format_type == "custom":
        if not check_custom_md5file_header(md5_filepath, False):
            raise ValueError(
                f"'{md5_filepath}' does not contain header for format_type 'custom'"
            )
        extract_filepath = CustomMD5Line.extract_filepath
        extract_checksum = CustomMD5Line.extract_checksum
    elif format_type == "custom_nested":
        if not check_custom_md5file_header(md5_filepath, True):
            raise ValueError(
                f"'{md5_filepath}' does not contain header for format_type 'custom_nested'"
            )
        extract_filepath = CustomMD5Line.extract_filepath
        extract_checksum = CustomMD5Line.extract_checksum
    elif format_type == "teracopy":
        extract_filepath = TeracopyMD5Line.extract_filepath
        extract_checksum = TeracopyMD5Line.extract_checksum

    # store extracted filepaths and checksums in corresponding order
    filepaths, checksums = [], []
    for line in md5_lines:
        line = unicodedata.normalize("NFC", line)

        # skip/ignore header lines
        if line[0] == "ï" or line[0] == ";" or line == "\n":
            continue

        filepaths.append(extract_filepath(line))
        checksums.append(extract_checksum(line))

    return filepaths, checksums


def md5(filepath: str) -> str:
    """Calculates MD5 checksum for file at `filepath`

    Args:
        filepath (str): Path to file to be checksummed.

    Returns:
        str: hex string representation of MD5 checksum of `filepath`

    """
    md5_hash = hashlib.md5()
    with open(filepath, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def revert_md5file_to_teracopy_format(
    path_to_formatted_file: str, save_filepath: str
) -> None:
    """Converts a file using custom_md5line format to a TeraCopy .md5 file

    Args:
        path_to_formatted_file (str): Filepath to file using custom_md5line
            format.
        save_filepath (str): Filepath to save converted file to/as. If file
            already exists, it will be OVERWRITTEN.

    """
    filepaths, checksums = extract_from_md5file(path_to_formatted_file, "custom")

    with open(save_filepath, "w+") as write_file:
        # write TeraCopy header (most likely not be necessary)
        write_file.write("; MD5 checksums created by TeraCopy\n")
        write_file.write("; teracopy.com\n\n")

        # create and write Teracopy MD5 line for each filepath/checksum pair
        for filepath, checksum in zip(filepaths, checksums):
            write_file.write(
                TeracopyMD5Line.get_teracopy_md5line_string(filepath, checksum) + "\n"
            )


def finding_missing_files(folder_path: str, md5_filepath: str) -> list:
    """Finds filepaths in "custom" checksum file that do not exist

    Args:
        folder_path (str): Path to folder where files in `md5_filepath` were
            checksummed (checksum filepaths are relative to this folder). This
            is the location where existence of files will be checked.
        md5_filepath (str): Path to checksum file in "custom" format.

    Returns:
        list: list of filepaths that do not exist

    """
    filepaths, _ = extract_from_md5file(md5_filepath, "custom")

    missing_files = []

    for filepath in filepaths:
        full_path = concat_filepaths(folder_path, filepath)
        if not os.path.exists(full_path):
            missing_files.append(filepath)

    return missing_files


def remove_checksums(
    md5_filepath: str,
    filepaths: list,
    save_orig: bool = True,
    require_confirmation: bool = True,
) -> tuple[str, list]:
    """Removes lines from "custom" checksum file

    Either `filepaths` of `checksums` must be specified. If a line's checksum
    or filepath is in `filepaths` or `checksums`, then it will be removed.

    Args:
        md5_filepath (str): Path to checksum file in "custom" format.
        filepaths (list): List of filepaths to remove from checksum file at
            `md5_filepath`.
        save_orig (bool, optional): If True, original `md5_filepath` will be
            saved (renamed first), otherwise it will just be overwritten.
            Defaults to True.
        require_confirmation (bool, optional): If True, asks before removing.
            Defaults to True.

    Raises:
        ValueError: `md5_filepath` does not contain expected header for
            "custom" format

    Returns:
        tuple[str, list]: filepath (str) to checksum file with lines removed,
            and list of the removed lines

    """
    # convert to set for faster search
    filepaths = set(filepaths)

    # read all lines from md5_filepath
    with open(md5_filepath, "r") as file:
        lines = file.readlines()

    # check md5_filepath is in "custom" format
    try:
        lines.remove(main_checksum_header + "\n")
    except ValueError:
        raise ValueError(
            f"'{md5_filepath}' does not contain header for format_type 'custom'"
        )

    # sort lines to keep and lines to remove into two lists
    lines_to_write = [main_checksum_header + "\n"]
    removed_lines = []

    for line in lines:
        filepath, checksum = extract_from_md5line(line, "custom")

        # check whether to remove line
        if filepath in filepaths:
            removing = ""
            if not require_confirmation:
                removing = "y"

            while removing != "y" and removing != "n":
                removing = input(f"Remove '{line}'? [y/n]: ").lower()

            if removing.lower() == "y":
                removed_lines.append(line)
            else:
                lines_to_write.append(line)
        else:
            lines_to_write.append(line)

    # write to file
    save_path = os.path.split(clean_filepath(md5_filepath))[0]
    save_location = get_checksum_save_location(save_path, not save_orig)
    append_unique_lines_to_file(save_location, lines_to_write)

    return save_location, removed_lines


def separate_by_dirs(filepaths: list, checksums: list):
    """Separates filepaths into arrays based on their parent directory

    Args:
        filepaths (list): List of filepaths to separate.
        checksums (list): List of values corresponding to `filepaths`, which
            will be separated identically. Defaults to None.

    Raises:
        ValueError: If `filepaths` contain identical filepaths with different
            checksums

    Returns:
        tuple[list, list, list]: lists for: [0] unique parent directories,
            [1] lists of filenames, one for each unique parent directories,
            [2] their corresponding checksums

    """
    # paths of parent directories of files in filepaths
    dirpaths = []
    # contains an array of filenames/checksums for each path in dirpaths
    dirpath_filenames = []
    dirpath_checksums = []

    for filepath, checksum in zip(filepaths, checksums):
        line_dirpath, filename = os.path.split(filepath)

        x = index_if_possible(dirpaths, line_dirpath)
        if x == -1:  # new parent directory
            dirpaths.append(line_dirpath)
            dirpath_filenames.append([filename])
            dirpath_checksums.append([checksum])
        else:  # parent directory already in dirpaths
            y = index_if_possible(dirpath_filenames, filename)
            if y == -1:  # new filename in dirpath
                dirpath_filenames[x].append(filename)
                dirpath_checksums[x].append(checksum)
            elif checksum != dirpath_checksums[y]:
                raise ValueError(
                    "filepaths: contains identical filepaths with different checksums"
                )

    return dirpaths, dirpath_filenames, dirpath_checksums


def separate_by_uniqueness(filenames: list, checksums: list):
    """Separates filenames into arrays depending on whether they are unique

    Args:
        filenames (list): List of filenames to separate.
        checksums (list): List of values corresponding to `filenames`, which
            will be separated identically. Defaults to None.

    Returns:
        tuple[list, list, list, list]: lists for: [0] unique filenames,
            [1] their corresponding checksums, [2] non-unique filenames,
            [3] their corresponding checksums

    """
    unique_filenames, unique_checksums = [], []
    non_unique_filenames, non_unique_checksums = [], []

    for filename, checksum in zip(filenames, checksums):
        dupe_idx = index_if_possible(non_unique_filenames, filename)

        if dupe_idx == -1:  # filename is not a duplicate of a non-unique filename
            idx = index_if_possible(unique_filenames, filename)

            if idx == -1:  # filename is not a duplicate a previously unique filename
                unique_filenames.append(filename)
                unique_checksums.append(checksum)
            else:  # filename is a duplicate of a previously unique filename
                non_unique_filenames.append(unique_filenames.pop(idx))
                non_unique_checksums.append(unique_checksums.pop(idx))
                non_unique_filenames.append(filename)
                non_unique_checksums.append(checksum)

        else:  # filename is a duplicate of a non-unique filename
            non_unique_filenames.append(filename)
            non_unique_checksums.append(checksum)

    return (
        unique_filenames,
        unique_checksums,
        non_unique_filenames,
        non_unique_checksums,
    )
