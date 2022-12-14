"""Utilities for MD5 files

Contains the following functions:
    * get_checksum_save_location
    * check_custom_md5file_header
    * extract_from_md5file
    * md5
    * revert_md5file_to_teracopy
    * separate_by_dirs
    * separate_by_uniqueness

"""

import os
import hashlib
import unicodedata

from utils import clean_filepath, index_if_possible
from md5lines import MD5Line, TeracopyMD5Line, CustomMD5Line


nested_checksum_header = "; nested_checksum"
main_checksum_header = "; main_checksum"

accepted_format_types = ["md5", "custom", "custom_nested", "teracopy"]

files_to_ignore = [".DS_Store", ".main_checksum.txt", ".nested_checksum.txt", "main_shipped.txt"]


def get_checksum_save_location(
    folder: str, updating_only: bool, nested: bool = False
) -> str:
    """Gets filepath to a custom MD5 checksum file

    The filename of the filepath will be ".nested_checksum.txt" if nested, or
    ".main_checksum.txt" otherwise.

    Args:
        folder (str): Path to directory that custom MD5 checksum file is for.
        updating_only (str): If true, will return path to latest checksum file
            that already exists if possible. If false, the returned path will
            be a new one (no existing file).
        nested (bool, optional): If true, the filename will indicate a nested
            file. If false, it will indicate a main checksum file. Defaults to
            False.

    Returns:
        str: save location for custom MD5 file, which is a filepath to a file
            (that may not exist) in `folder`

    """
    # folder path must not have trailing slash - remove if necessary
    folder = clean_filepath(folder, False)

    if nested:
        orig_save_location = folder + "/.nested_checksum.txt"
    else:
        orig_save_location = folder + f"/.main_checksum.txt"

    save_location = orig_save_location
    save_location_template = os.path.splitext(save_location)[0] + "_{}.txt"

    # iterate count until filename does not exist
    count = 0
    while os.path.exists(save_location):
        count += 1
        save_location = save_location_template.format(count)

    if updating_only and count != 0:
        # decrement count to get latest filename that exists
        if count == 1:
            save_location = orig_save_location
        else:
            save_location = save_location_template.format(count - 1)

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
        if line[0] == "??" or line[0] == ";" or line == "\n":
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
