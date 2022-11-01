import re

import utils
from md5lines import MD5Line


class TeracopyMD5Line(MD5Line):
    """Represents a MD5 line generated by TeraCopy's verify option.

    TeraCopy is a file transfer utility / copy handler, and the generated
    line is in the format f"{checksum} *{filepath}".

    """

    def __init__(self, teracopy_md5_line: str, reroot_dir: str = None) -> None:
        """
        Args:
            teracopy_md5_line (str): A string in the format
                f"{checksum} *{filepath}".
            reroot_dir (str, optional): If specified, filepath in
                `teracopy_md5_line` will be modified to be relative to
                `reroot_dir`. Defaults to None.

        Raises:
            ValueError: If `teracopy_md5_line` is not in expected format

        """
        if not TeracopyMD5Line.validate_md5line(teracopy_md5_line):
            raise ValueError("teracopy_md5_line: format should be 'checksum *filepath'")

        self._orig_teracopy_md5_line = MD5Line.clean_md5line(teracopy_md5_line)
        self._teracopy_md5_line_reroot_dir = reroot_dir

        checksum = TeracopyMD5Line.extract_checksum(teracopy_md5_line)
        filepath = TeracopyMD5Line.extract_filepath(teracopy_md5_line, reroot_dir)
        md5_line = MD5Line.get_md5line_string(filepath, checksum)

        super().__init__(md5_line, reroot_dir)

    def get_string(self) -> str:
        return TeracopyMD5Line.get_teracopy_md5line_string(self.filepath, self.checksum)

    @property
    def orig_teracopy_md5_line(self) -> str:
        """str: original TeraCopy MD5 line used in initialisation"""
        return self._orig_teracopy_md5_line

    @property
    def teracopy_md5_line_reroot_dir(self) -> str:
        """str: dir that filepath was made relative to"""
        return self._teracopy_md5_line_reroot_dir

    @staticmethod
    def validate_md5line(md5_line: str) -> bool:
        """checks that `md5_line` is formatted correctly to be a teracopy_md5line"""
        ## only checks string contains a md5 checksum in the right place
        if re.match("^[A-Fa-f0-9]{32}$", md5_line.split(" *")[0]):
            return True

        return False

    @staticmethod
    def extract_checksum(teracopy_md5_line: str) -> str:
        if not TeracopyMD5Line.validate_md5line(teracopy_md5_line):
            raise ValueError("teracopy_md5_line: format should be 'checksum *filepath'")

        return MD5Line.clean_md5line(teracopy_md5_line).split(" *")[0]

    @staticmethod
    def extract_filepath(teracopy_md5_line: str, reroot_dir: str = None) -> str:
        if not TeracopyMD5Line.validate_md5line(teracopy_md5_line):
            raise ValueError("teracopy_md5_line: format should be 'checksum *filepath'")

        filepath = MD5Line.clean_md5line(teracopy_md5_line).split(" *", 1)[1]
        return utils.make_relative_path(filepath, reroot_dir)

    @staticmethod
    def get_teracopy_md5line_string(filepath: str, checksum: str) -> str:
        return f"{checksum} *{filepath}"
