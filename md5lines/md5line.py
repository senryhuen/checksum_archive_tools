import re

import utils


class MD5Line:
    """Represents a line generated from 'md5sum' command on Linux Systems.

    The line format is f"{checksum} {filepath}", On macOS, 'md5 -r' will
    produce the same format.

    """

    def __init__(self, md5_line: str, reroot_dir: str = None):
        """
        Args:
            md5_line (str): A string in the format f"{checksum} {filepath}".
            reroot_dir (str, optional): If specified, filepath in
                `md5_line` will be modified to be relative to `reroot_dir`.
                Defaults to None.

        Raises:
            ValueError: If `md5_line` is not in expected format

        """
        if not MD5Line.validate_md5line(md5_line):
            raise ValueError("md5_line: format should be 'checksum filepath'")

        self._orig_md5_line = MD5Line.clean_md5line(md5_line)
        self._md5_line_reroot_dir = reroot_dir

        self._checksum = MD5Line.extract_checksum(md5_line)
        self._filepath = MD5Line.extract_filepath(md5_line, reroot_dir)
        self._md5_line = MD5Line.get_md5line_string(self.filepath, self.checksum)

    def get_string(self) -> str:
        return self.md5_line

    @property
    def orig_md5_line(self) -> str:
        """str: original MD5 line used in initialisation"""
        return self._orig_md5_line

    @property
    def md5_line_reroot_dir(self) -> str:
        """str: dir that filepath was made relative to"""
        return self._md5_line_reroot_dir

    @property
    def checksum(self) -> str:
        return self._checksum

    @property
    def filepath(self) -> str:
        return self._filepath

    # allows subclasses that represent MD5 lines in a different format to easily get the equivalent line in this format
    @property
    def md5_line(self) -> str:
        return self._md5_line

    @staticmethod
    def validate_md5line(md5_line: str) -> bool:
        """checks that `md5_line` is formatted correctly to be a md5line"""
        ## only checks first part of the string is a md5 checksum, assumes second part is a filepath
        if re.match("^[A-Fa-f0-9]{32}$", md5_line.split()[0]):
            return True

        return False

    @staticmethod
    def clean_md5line(md5_line: str) -> str:
        """removes newline character and normalises filepaths (to forward slashes)"""
        return md5_line.replace("\n", "").replace("\\", "/")

    @staticmethod
    def extract_checksum(md5_line: str) -> str:
        if not MD5Line.validate_md5line(md5_line):
            raise ValueError("md5_line: format should be 'checksum filepath'")

        return MD5Line.clean_md5line(md5_line).split(" ./")[0]

    @staticmethod
    def extract_filepath(md5_line: str, reroot_dir: str = None) -> str:
        if not MD5Line.validate_md5line(md5_line):
            raise ValueError("md5_line: format should be 'checksum filepath'")

        filepath = f"./{MD5Line.clean_md5line(md5_line).split(' ./', 1)[1]}"
        return utils.make_relative_path(filepath, reroot_dir)

    @staticmethod
    def get_md5line_string(filepath: str, checksum: str) -> str:
        return f"{checksum} {filepath}"
