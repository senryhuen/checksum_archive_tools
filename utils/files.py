"""Utilities for handling files / paths

Contains the following functions:
    * get_dir_size
    * clean_filepath
    * make_relative_path
    * concat_filepaths
    * append_unique_lines_to_file

"""

import os
import unicodedata


def get_dir_size(dir_path: str, max_decimals: int = 3) -> float:
    """Gets filesize of a directory (all of its contents combined) in GiBs

    Args:
        dir_path (str): Path to directory to get filesize of.
        max_decimals (int, optional): Rounds filesize to max_decimals.
            Defaults to 3.

    Returns:
        float: filesize of directory in gibibytes (GiB)

    """
    total_filesize_bytes = 0

    for root, dirs, files in os.walk(dir_path):
        for file in files:
            total_filesize_bytes += os.path.getsize(root + "/" + file)

    total_filesize_gigabytes = total_filesize_bytes / (1024**3)
    return round(total_filesize_gigabytes, max_decimals)


def clean_filepath(filepath: str, allow_trailing_slash: bool = False) -> str:
    """Cleans filepath to return a filepath that follows local standard

    Normalises filepath to use forward slash rather than backslash and removes
    trailing slash depending on `allow_trailing_slash`.

    Args:
        filepath (str): Filepath to be cleaned.
        allow_trailing_slash (bool, optional): If True, trailing slashes will
            not be removed. Defaults to False.

    Returns:
        str: cleaned `filepath`

    """
    filepath = filepath.replace("\\", "/")

    if not allow_trailing_slash:
        while filepath[-1] == "/":
            filepath = filepath[:-1]

    return filepath


def make_relative_path(path: str, root_dir: str) -> str:
    """Makes `path` a relative path from `root_dir`

    Replaces everything before and including `root_dir` in `path` with './'.

    Example:
        ``make_relative_path("this/is/a/path", "is")``  -->
        ``"./a/path"``

    If `root_dir` is not in `path`, then nothing is done.

    If multiple directories in `path` match `root_dir`, then the outer most
    match (first match from left to right) is used. To use a nested dir within
    multiple matches, a path to that nested dir should be specified.

    Args:
        path (str): A path to make relative to `root_dir`.
        root_dir (str): Directory (in `path`) to make `path` relative to.

    Returns:
        str: `path` modified to be relative from `root_dir`

    """
    path = unicodedata.normalize("NFC", path.replace("\\", "/"))

    if root_dir is None:
        return path

    root_dir = unicodedata.normalize("NFC", root_dir.replace("\\", "/"))

    if root_dir in path:
        path = "/" + path + "/"
        split_path = path.split(f"/{root_dir}/".replace("//", "/"), 1)
        path = f"./{split_path[1][:-1]}"

    if path == "./":
        path = "."

    return path


def concat_filepaths(
    first_path: str, second_path: str, allow_trailing_slash: bool = False
) -> str:
    """Concatenate filepaths with absolute paths treated equally

    `os.path.join` will discard everything before a component if it is an
    absolute path (starts with a '/'). `concat_filepaths` will join all
    components regardless.

    If `second_path` is an absolute or relative path, the leading '/' or './'
    will be ignored so that is can be joined onto `first_path` to form a valid
    path.

    Example:
        ``concat_filepaths("this/is/a/path/", "/another/path")``  -->
        ``"this/is/a/path/another/path"``

        ``os.path.join("this/is/a/path/", "/another/path")``  -->
        ``"/another/path"``

    Args:
        first_path (str): A filepath which `second_path` will be added to.
        second_path (str): A filepath to append to `first_path`.
        allow_trailing_slash (bool, optional): If True, trailing slashes will
            not be removed from the concatenated filepath. Defaults to False.

    Returns:
        str: a filepath that is `second_path` joined onto `first_path`,
            normalised to '\\' or '/' depending on platform being run on

    """
    first_path = clean_filepath(first_path, True)
    second_path = clean_filepath(second_path, allow_trailing_slash)

    # ensure first path ends with trailing slash
    if first_path[-1] != "/":
        first_path += "/"

    # ensure second path does not start with slash or relative path
    if second_path[0] == "/":
        second_path = second_path[1:]
    elif second_path[:2] == "./":
        second_path = second_path[2:]

    return os.path.join(first_path, second_path)


def append_unique_lines_to_file(filepath: str, lines: list) -> None:
    """Appends/writes lines to a file if they do not already exist in the file

    If the file specified by `filepath` does not exist, it will be created.

    Args:
        filepath (str): Path to file to append/write lines to.
        lines (list): List of lines (str) to be written.

    """
    if not os.path.exists(filepath):
        with open(filepath, "w+") as file:
            for line in lines:
                file.write(line)
    else:
        with open(filepath, "r") as file:
            existing_lines = file.readlines()

        with open(filepath, "a") as file:
            for line in lines:
                if line not in existing_lines:
                    file.write(line)
