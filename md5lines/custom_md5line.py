import os
import re

import utils
from md5lines import MD5Line


class CustomMD5Line(MD5Line):
    """Represents a line in a custom format as stored in generated checksum files.

    The line format is f"{filepath} -> {checksum}".

    """

    def __init__(self, custom_md5_line: str, reroot_dir: str = None):
        """
        Args:
            custom_md5_line (str): A string in the format
                f"{filepath} -> {checksum}".
            reroot_dir (str, optional): If specified, filepath in
                `custom_md5_line` will be modified to be relative to
                `reroot_dir`. Defaults to None.

        Raises:
            ValueError: If `custom_md5_line` is not in expected format

        """
        if not CustomMD5Line.validate_md5line(custom_md5_line):
            raise ValueError("custom_md5_line: format should be 'filepath -> checksum'")

        self._orig_custom_md5_line = MD5Line.clean_md5line(custom_md5_line)
        self._custom_md5_line_reroot_dir = reroot_dir

        checksum = CustomMD5Line.extract_checksum(custom_md5_line)
        filepath = CustomMD5Line.extract_filepath(custom_md5_line, reroot_dir)
        md5_line = MD5Line.get_md5line_string(filepath, checksum)
        super().__init__(md5_line)

    def get_string(self, short_format: bool = False) -> str:
        """
        Args:
            short_format (bool, optional): If True, filename will be used
                instead of filepath in custom_md5line. Defaults to False.

        Returns:
            str: current object as string in custom_md5line format

        """
        if short_format:
            return self.get_short_custom_md5line_string(self.filepath, self.checksum)
        return self.get_custom_md5line_string(self.filepath, self.checksum)

    @property
    def orig_custom_md5_line(self) -> str:
        """str: original custom MD5 line used in initialisation"""
        return self._orig_custom_md5_line

    @property
    def custom_md5_line_reroot_dir(self) -> str:
        """str: dir that filepath was made relative to"""
        return self._custom_md5_line_reroot_dir

    @staticmethod
    def validate_md5line(md5_line: str) -> bool:
        """checks that `md5_line` is formatted correctly to be a custom_md5line"""
        ## only checks string contains a md5 checksum in the right place
        if re.match("^[A-Fa-f0-9]{32}$", MD5Line.clean_md5line(md5_line).rsplit(" -> ", 1)[1]):
            return True

        return False

    @staticmethod
    def extract_checksum(custom_md5_line: str) -> str:
        if not CustomMD5Line.validate_md5line(custom_md5_line):
            raise ValueError("custom_md5_line: format should be 'filepath -> checksum'")

        return MD5Line.clean_md5line(custom_md5_line).rsplit(" -> ", 1)[1]

    @staticmethod
    def extract_filepath(custom_md5_line: str, reroot_dir: bool = None) -> str:
        if not CustomMD5Line.validate_md5line(custom_md5_line):
            raise ValueError("custom_md5_line: format should be 'filepath -> checksum'")

        filepath = MD5Line.clean_md5line(custom_md5_line).rsplit(" -> ", 1)[0]
        return utils.make_relative_path(filepath, reroot_dir)

    @staticmethod
    def get_custom_md5line_string(filepath: str, checksum: str) -> str:
        return f"{filepath} -> {checksum}"

    @staticmethod
    def get_short_custom_md5line_string(filepath: str, checksum: str) -> str:
        """short custom_md5_line format uses filename in place of filepath"""
        filename = os.path.basename(filepath)
        return f"{filename} -> {checksum}"
