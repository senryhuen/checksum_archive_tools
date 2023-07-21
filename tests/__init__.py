import unittest
import os
import shutil
from md5files import *


OLD_FILENAME = os.path.splitext(MAIN_CHECKSUM_FILENAME)[0] + "_old.txt"
OLD_NESTED_FILENAME = os.path.splitext(NESTED_CHECKSUM_FILENAME)[0] + "_old.txt"

TESTFILES_PATH = "testfiles"
MAIN_CHECKSUM_PATH = f"{TESTFILES_PATH}/{MAIN_CHECKSUM_FILENAME}"
OLD_MAIN_CHECKSUM_PATH = f"{TESTFILES_PATH}/{OLD_FILENAME}"

HEADER_LINE = "; main_checksum\n"
TEST1_LINE = "./test1.txt -> c4ca4238a0b923820dcc509a6f75849b\n"
TEST2_LINE = "./test2.txt -> c81e728d9d4c2f636f067f89cc14862c\n"
TEST11_LINE = "./1/test11.txt -> 6512bd43d9caa6e02c990b0a82652dca\n"
TEST121_LINE = "./1/2/test121.txt -> 4c56ff4ce4aaf9573aa5dff913df997a\n"
TEST122_LINE = "./1/2/test122.txt -> c4ca4238a0b923820dcc509a6f75849b\n"
TEST21_LINE = "./2/test21.txt -> 3c59dc048e8850243be8079a5c74d079\n"
TEST21_2_LINE = "./1/2/test21.txt -> 3c59dc048e8850243be8079a5c74d079\n"
TEST11_2_LINE = "./1/2/test11.txt -> 3c59dc048e8850243be8079a5c74d079\n"  # wrong checksum
