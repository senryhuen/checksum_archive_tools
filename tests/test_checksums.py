from tests import *


class TestChecksums(unittest.TestCase):
    # for testing generate_checksums (without using unsorted_source) and related functions

    @classmethod
    def setUpClass(cls) -> None:
        # create folder structure and files to generate checksums for
        if os.path.exists(TESTFILES_PATH):
            shutil.rmtree(TESTFILES_PATH)

        os.makedirs(f"{TESTFILES_PATH}/1")
        os.makedirs(f"{TESTFILES_PATH}/2")
        os.makedirs(f"{TESTFILES_PATH}/1/1")
        os.makedirs(f"{TESTFILES_PATH}/1/2")

        with open(f"{TESTFILES_PATH}/test1.txt", "w+", encoding="utf8") as file:
            file.write("1")
        with open(f"{TESTFILES_PATH}/test2.txt", "w+", encoding="utf8") as file:
            file.write("2")
        with open(f"{TESTFILES_PATH}/1/test11.txt", "w+", encoding="utf8") as file:
            file.write("11")
        with open(f"{TESTFILES_PATH}/2/test21.txt", "w+", encoding="utf8") as file:
            file.write("21")
        with open(f"{TESTFILES_PATH}/1/2/test121.txt", "w+", encoding="utf8") as file:
            file.write("121")
        with open(f"{TESTFILES_PATH}/1/2/test122.txt", "w+", encoding="utf8") as file:
            file.write("1")

    @classmethod
    def tearDownClass(cls) -> None:
        # delete created folder and contents
        if os.path.exists(TESTFILES_PATH):
            shutil.rmtree(TESTFILES_PATH)

    def tearDown(self):
        # delete checksum files in testfiles folder
        for root, _, files in os.walk(TESTFILES_PATH):
            for file in files:
                if is_checksum_filename(file, incl_old=True):
                    os.remove(os.path.join(root, file))

    def check_no_main_checksum_files(self):
        self.assertFalse(os.path.exists(MAIN_CHECKSUM_PATH))
        self.assertFalse(os.path.exists(OLD_MAIN_CHECKSUM_PATH))

    def check_expected_main_checksum_contents(self):
        with open(MAIN_CHECKSUM_PATH, "r", encoding="utf8") as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 7)
            self.assertTrue(HEADER_LINE in lines)
            self.assertTrue(TEST1_LINE in lines)
            self.assertTrue(TEST2_LINE in lines)
            self.assertTrue(TEST11_LINE in lines)
            self.assertTrue(TEST121_LINE in lines)
            self.assertTrue(TEST122_LINE in lines)
            self.assertTrue(TEST21_LINE in lines)

    def test_correct_checksums(self):
        generate_checksums(TESTFILES_PATH, False)
        self.assertTrue(os.path.isfile(MAIN_CHECKSUM_PATH))
        self.check_expected_main_checksum_contents()

    def test_updates_file_when_updating_only(self):
        self.check_no_main_checksum_files()

        # ignore a file to check it is checksummed on next run with updating_only=True
        generate_checksums(TESTFILES_PATH, False, files_to_ignore=["test21.txt"])
        self.assertTrue(os.path.isfile(MAIN_CHECKSUM_PATH))
        self.assertFalse(os.path.exists(OLD_MAIN_CHECKSUM_PATH))

        with open(MAIN_CHECKSUM_PATH, "r", encoding="utf8") as file:
            lines = file.readlines()
            self.assertFalse(TEST21_LINE in lines)
            self.assertTrue(TEST122_LINE in lines)

        generate_checksums(TESTFILES_PATH, True)
        self.assertTrue(os.path.isfile(MAIN_CHECKSUM_PATH))
        self.assertFalse(os.path.exists(OLD_MAIN_CHECKSUM_PATH))

        self.check_expected_main_checksum_contents()

    def test_checksums_not_removed_when_updating_only(self):
        self.check_no_main_checksum_files()

        generate_checksums(TESTFILES_PATH, False)
        self.assertTrue(os.path.isfile(MAIN_CHECKSUM_PATH))
        self.assertFalse(os.path.exists(OLD_MAIN_CHECKSUM_PATH))

        self.check_expected_main_checksum_contents()

        # ignore a file then check it is not removed from checksums
        generate_checksums(TESTFILES_PATH, True, files_to_ignore=["test21.txt"])
        self.assertTrue(os.path.isfile(MAIN_CHECKSUM_PATH))
        self.assertFalse(os.path.exists(OLD_MAIN_CHECKSUM_PATH))

        self.check_expected_main_checksum_contents()

    def test_renames_old_file_when_not_updating_only(self):
        self.check_no_main_checksum_files()

        # ignore a file to check old checksum file not modified on next run with updating_only=False
        generate_checksums(TESTFILES_PATH, False, files_to_ignore=["test21.txt"])
        self.assertTrue(os.path.isfile(MAIN_CHECKSUM_PATH))
        self.assertFalse(os.path.exists(OLD_MAIN_CHECKSUM_PATH))

        generate_checksums(TESTFILES_PATH, False)
        self.assertTrue(os.path.isfile(MAIN_CHECKSUM_PATH))
        self.assertTrue(os.path.exists(OLD_MAIN_CHECKSUM_PATH))

        # check old checksum file does not contain the new checksum
        with open(OLD_MAIN_CHECKSUM_PATH, "r", encoding="utf8") as file:
            self.assertFalse(TEST21_LINE in file.readlines())
        with open(MAIN_CHECKSUM_PATH, "r", encoding="utf8") as file:
            self.assertTrue(TEST21_LINE in file.readlines())

    def test_skips_single_files_to_ignore_from_list(self):
        generate_checksums(TESTFILES_PATH, False, files_to_ignore=["test21.txt"])

        with open(MAIN_CHECKSUM_PATH, "r", encoding="utf8") as file:
            lines = file.readlines()
            self.assertFalse(TEST21_LINE in lines)
            self.assertTrue(TEST122_LINE in lines)

        generate_checksums(TESTFILES_PATH, True)

        self.check_expected_main_checksum_contents()

    def test_skips_multiple_files_to_ignore_from_list(self):
        generate_checksums(
            TESTFILES_PATH, False, files_to_ignore=["test21.txt", "test122.txt"]
        )

        with open(MAIN_CHECKSUM_PATH, "r", encoding="utf8") as file:
            lines = file.readlines()
            self.assertFalse(TEST21_LINE in lines)
            self.assertFalse(TEST122_LINE in lines)
            self.assertTrue(TEST121_LINE in lines)

        generate_checksums(TESTFILES_PATH, True)

        self.check_expected_main_checksum_contents()

    def test_create_nested_checksums(self):
        generate_checksums(TESTFILES_PATH, False)

        self.assertFalse(os.path.exists(f"{TESTFILES_PATH}/{NESTED_CHECKSUM_FILENAME}"))
        self.assertFalse(
            os.path.exists(f"{TESTFILES_PATH}/1/{NESTED_CHECKSUM_FILENAME}")
        )
        self.assertFalse(
            os.path.exists(f"{TESTFILES_PATH}/1/1/{NESTED_CHECKSUM_FILENAME}")
        )
        self.assertFalse(
            os.path.exists(f"{TESTFILES_PATH}/1/2/{NESTED_CHECKSUM_FILENAME}")
        )
        self.assertFalse(
            os.path.exists(f"{TESTFILES_PATH}/2/{NESTED_CHECKSUM_FILENAME}")
        )

        nest_checksums(TESTFILES_PATH, False)

        self.assertTrue(os.path.exists(f"{TESTFILES_PATH}/{NESTED_CHECKSUM_FILENAME}"))
        self.assertTrue(
            os.path.exists(f"{TESTFILES_PATH}/1/{NESTED_CHECKSUM_FILENAME}")
        )
        self.assertFalse(
            os.path.exists(f"{TESTFILES_PATH}/1/1/{NESTED_CHECKSUM_FILENAME}")
        )
        self.assertTrue(
            os.path.exists(f"{TESTFILES_PATH}/1/2/{NESTED_CHECKSUM_FILENAME}")
        )
        self.assertTrue(
            os.path.exists(f"{TESTFILES_PATH}/2/{NESTED_CHECKSUM_FILENAME}")
        )

    def test_nested_checksums_contents_correct(self):
        generate_checksums(TESTFILES_PATH, False)
        nest_checksums(TESTFILES_PATH, False)

        # also tests main_checksum file ignored
        with open(
            f"{TESTFILES_PATH}/{NESTED_CHECKSUM_FILENAME}", "r", encoding="utf8"
        ) as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 3)
            self.assertTrue(f"{NESTED_CHECKSUM_HEADER}\n" in lines)
            self.assertTrue(f"{CustomMD5Line(TEST1_LINE).get_string(True)}\n" in lines)
            self.assertTrue(f"{CustomMD5Line(TEST2_LINE).get_string(True)}\n" in lines)

        with open(
            f"{TESTFILES_PATH}/1/{NESTED_CHECKSUM_FILENAME}", "r", encoding="utf8"
        ) as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 2)
            self.assertTrue(f"{NESTED_CHECKSUM_HEADER}\n" in lines)
            self.assertTrue(f"{CustomMD5Line(TEST11_LINE).get_string(True)}\n" in lines)

        with open(
            f"{TESTFILES_PATH}/1/2/{NESTED_CHECKSUM_FILENAME}", "r", encoding="utf8"
        ) as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 3)
            self.assertTrue(f"{NESTED_CHECKSUM_HEADER}\n" in lines)
            self.assertTrue(
                f"{CustomMD5Line(TEST121_LINE).get_string(True)}\n" in lines
            )
            self.assertTrue(
                f"{CustomMD5Line(TEST122_LINE).get_string(True)}\n" in lines
            )

        with open(
            f"{TESTFILES_PATH}/2/{NESTED_CHECKSUM_FILENAME}", "r", encoding="utf8"
        ) as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 2)
            self.assertTrue(f"{NESTED_CHECKSUM_HEADER}\n" in lines)
            self.assertTrue(f"{CustomMD5Line(TEST21_LINE).get_string(True)}\n" in lines)

    def test_updates_nested_file_when_updating_only(self):
        generate_checksums(TESTFILES_PATH, False, files_to_ignore=["test121.txt"])
        nest_checksums(TESTFILES_PATH, False)
        self.assertFalse(os.path.exists(f"{TESTFILES_PATH}/1/2/{OLD_NESTED_FILENAME}"))

        # test files_to_ignore not in nested checksum file
        with open(
            f"{TESTFILES_PATH}/1/2/{NESTED_CHECKSUM_FILENAME}", "r", encoding="utf8"
        ) as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 2)
            self.assertTrue(f"{NESTED_CHECKSUM_HEADER}\n" in lines)
            self.assertFalse(
                f"{CustomMD5Line(TEST121_LINE).get_string(True)}\n" in lines
            )
            self.assertTrue(
                f"{CustomMD5Line(TEST122_LINE).get_string(True)}\n" in lines
            )

        generate_checksums(TESTFILES_PATH, True)
        nest_checksums(TESTFILES_PATH, True)
        self.assertFalse(os.path.exists(f"{TESTFILES_PATH}/1/2/{OLD_NESTED_FILENAME}"))

        # test previously skipped line is now in nested checksum file
        with open(
            f"{TESTFILES_PATH}/1/2/{NESTED_CHECKSUM_FILENAME}", "r", encoding="utf8"
        ) as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 3)
            self.assertTrue(f"{NESTED_CHECKSUM_HEADER}\n" in lines)
            self.assertTrue(
                f"{CustomMD5Line(TEST121_LINE).get_string(True)}\n" in lines
            )
            self.assertTrue(
                f"{CustomMD5Line(TEST122_LINE).get_string(True)}\n" in lines
            )

    def test_nested_checksums_not_removed_when_updating_only(self):
        generate_checksums(TESTFILES_PATH, False)
        nest_checksums(TESTFILES_PATH, False)
        self.assertFalse(os.path.exists(f"{TESTFILES_PATH}/1/2/{OLD_NESTED_FILENAME}"))

        with open(
            f"{TESTFILES_PATH}/1/2/{NESTED_CHECKSUM_FILENAME}", "r", encoding="utf8"
        ) as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 3)
            self.assertTrue(f"{NESTED_CHECKSUM_HEADER}\n" in lines)
            self.assertTrue(
                f"{CustomMD5Line(TEST121_LINE).get_string(True)}\n" in lines
            )
            self.assertTrue(
                f"{CustomMD5Line(TEST122_LINE).get_string(True)}\n" in lines
            )

        generate_checksums(TESTFILES_PATH, False, files_to_ignore=["test121.txt"])
        nest_checksums(TESTFILES_PATH, True)
        self.assertFalse(os.path.exists(f"{TESTFILES_PATH}/1/2/{OLD_NESTED_FILENAME}"))

        with open(
            f"{TESTFILES_PATH}/1/2/{NESTED_CHECKSUM_FILENAME}", "r", encoding="utf8"
        ) as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 3)
            self.assertTrue(f"{NESTED_CHECKSUM_HEADER}\n" in lines)
            self.assertTrue(
                f"{CustomMD5Line(TEST121_LINE).get_string(True)}\n" in lines
            )
            self.assertTrue(
                f"{CustomMD5Line(TEST122_LINE).get_string(True)}\n" in lines
            )

    def test_renames_old_nested_file_when_not_updating_only(self):
        generate_checksums(TESTFILES_PATH, False, files_to_ignore=["test121.txt"])
        nest_checksums(TESTFILES_PATH, False)
        self.assertFalse(os.path.exists(f"{TESTFILES_PATH}/1/2/{OLD_NESTED_FILENAME}"))

        with open(
            f"{TESTFILES_PATH}/1/2/{NESTED_CHECKSUM_FILENAME}", "r", encoding="utf8"
        ) as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 2)
            self.assertTrue(f"{NESTED_CHECKSUM_HEADER}\n" in lines)
            self.assertFalse(
                f"{CustomMD5Line(TEST121_LINE).get_string(True)}\n" in lines
            )
            self.assertTrue(
                f"{CustomMD5Line(TEST122_LINE).get_string(True)}\n" in lines
            )

        generate_checksums(TESTFILES_PATH, False)
        nest_checksums(TESTFILES_PATH, False)
        self.assertTrue(os.path.exists(f"{TESTFILES_PATH}/1/2/{OLD_NESTED_FILENAME}"))

        with open(
            f"{TESTFILES_PATH}/1/2/{NESTED_CHECKSUM_FILENAME}", "r", encoding="utf8"
        ) as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 3)
            self.assertTrue(f"{NESTED_CHECKSUM_HEADER}\n" in lines)
            self.assertTrue(
                f"{CustomMD5Line(TEST121_LINE).get_string(True)}\n" in lines
            )
            self.assertTrue(
                f"{CustomMD5Line(TEST122_LINE).get_string(True)}\n" in lines
            )

        with open(
            f"{TESTFILES_PATH}/1/2/{OLD_NESTED_FILENAME}", "r", encoding="utf8"
        ) as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 2)
            self.assertTrue(f"{NESTED_CHECKSUM_HEADER}\n" in lines)
            self.assertFalse(
                f"{CustomMD5Line(TEST121_LINE).get_string(True)}\n" in lines
            )
            self.assertTrue(
                f"{CustomMD5Line(TEST122_LINE).get_string(True)}\n" in lines
            )

    def test_delete_nested_checksums(self):
        generate_checksums(TESTFILES_PATH, False)
        nest_checksums(TESTFILES_PATH, False)

        self.assertTrue(os.path.exists(f"{TESTFILES_PATH}/{NESTED_CHECKSUM_FILENAME}"))
        self.assertTrue(
            os.path.exists(f"{TESTFILES_PATH}/1/{NESTED_CHECKSUM_FILENAME}")
        )
        self.assertFalse(
            os.path.exists(f"{TESTFILES_PATH}/1/1/{NESTED_CHECKSUM_FILENAME}")
        )
        self.assertTrue(
            os.path.exists(f"{TESTFILES_PATH}/1/2/{NESTED_CHECKSUM_FILENAME}")
        )
        self.assertTrue(
            os.path.exists(f"{TESTFILES_PATH}/2/{NESTED_CHECKSUM_FILENAME}")
        )

        delete_nested_checksum_files(TESTFILES_PATH)

        self.assertFalse(os.path.exists(f"{TESTFILES_PATH}/{NESTED_CHECKSUM_FILENAME}"))
        self.assertFalse(
            os.path.exists(f"{TESTFILES_PATH}/1/{NESTED_CHECKSUM_FILENAME}")
        )
        self.assertFalse(
            os.path.exists(f"{TESTFILES_PATH}/1/1/{NESTED_CHECKSUM_FILENAME}")
        )
        self.assertFalse(
            os.path.exists(f"{TESTFILES_PATH}/1/2/{NESTED_CHECKSUM_FILENAME}")
        )
        self.assertFalse(
            os.path.exists(f"{TESTFILES_PATH}/2/{NESTED_CHECKSUM_FILENAME}")
        )


class TestChecksumsIndividual(unittest.TestCase):
    # same as TestChecksums but with setUp and tearDown before each test

    def setUp(self):
        # create folder structure and files to generate checksums for
        if os.path.exists(TESTFILES_PATH):
            shutil.rmtree(TESTFILES_PATH)

        os.makedirs(f"{TESTFILES_PATH}/1")
        os.makedirs(f"{TESTFILES_PATH}/2")
        os.makedirs(f"{TESTFILES_PATH}/1/2")

        with open(f"{TESTFILES_PATH}/test1.txt", "w+", encoding="utf8") as file:
            file.write("1")
        with open(f"{TESTFILES_PATH}/test2.txt", "w+", encoding="utf8") as file:
            file.write("2")
        with open(f"{TESTFILES_PATH}/1/test11.txt", "w+", encoding="utf8") as file:
            file.write("11")
        with open(f"{TESTFILES_PATH}/2/test21.txt", "w+", encoding="utf8") as file:
            file.write("21")
        with open(f"{TESTFILES_PATH}/1/2/test121.txt", "w+", encoding="utf8") as file:
            file.write("121")
        with open(f"{TESTFILES_PATH}/1/2/test122.txt", "w+", encoding="utf8") as file:
            file.write("1")

    def tearDown(self):
        # delete created folder and contents
        if os.path.exists(TESTFILES_PATH):
            shutil.rmtree(TESTFILES_PATH)

    def test_no_recalculation_when_updating_only(self):
        self.assertFalse(os.path.exists(MAIN_CHECKSUM_PATH))
        self.assertFalse(os.path.exists(OLD_MAIN_CHECKSUM_PATH))

        generate_checksums(TESTFILES_PATH, False)
        self.assertTrue(os.path.isfile(MAIN_CHECKSUM_PATH))
        self.assertFalse(os.path.exists(OLD_MAIN_CHECKSUM_PATH))

        with open(MAIN_CHECKSUM_PATH, "r", encoding="utf8") as file:
            lines = file.readlines()
            self.assertTrue(TEST21_LINE in lines)
            self.assertTrue(TEST122_LINE in lines)

        with open(f"{TESTFILES_PATH}/2/test21.txt", "w", encoding="utf8") as file:
            file.write("121")

        generate_checksums(TESTFILES_PATH, True)
        self.assertTrue(os.path.isfile(MAIN_CHECKSUM_PATH))
        self.assertFalse(os.path.exists(OLD_MAIN_CHECKSUM_PATH))

        # check checksum lines have not changed, even though file contents/checksum has changed
        with open(MAIN_CHECKSUM_PATH, "r", encoding="utf8") as file:
            lines = file.readlines()
            self.assertTrue(TEST21_LINE in lines)
            self.assertTrue(TEST122_LINE in lines)

    def test_skips_files_to_ignore_from_file(self):
        files_to_ignore_filepath = f"{TESTFILES_PATH}/files_to_ignore.txt"

        with open(files_to_ignore_filepath, "w", encoding="utf8") as file:
            file.write("files_to_ignore.txt\ntest1.txt")

        generate_checksums(
            TESTFILES_PATH, False, files_to_ignore_filepath=files_to_ignore_filepath
        )

        with open(MAIN_CHECKSUM_PATH, "r", encoding="utf8") as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 6)
            self.assertFalse(
                "./files_to_ignore.txt -> dea79f1e304b900fb86f897a76083534\n" in lines
            )
            self.assertFalse(TEST1_LINE in lines)
            self.assertTrue(TEST122_LINE in lines)

        generate_checksums(TESTFILES_PATH, True)

        with open(MAIN_CHECKSUM_PATH, "r", encoding="utf8") as file:
            lines = file.readlines()
            print(lines)
            self.assertEqual(len(lines), 8)
            self.assertTrue(
                "./files_to_ignore.txt -> dea79f1e304b900fb86f897a76083534\n" in lines
            )
            self.assertTrue(TEST1_LINE in lines)
            self.assertTrue(TEST122_LINE in lines)

    def test_remove_missing_checksums_without_save_orig(self):
        generate_checksums(TESTFILES_PATH, False)
        os.remove(f"{TESTFILES_PATH}/test1.txt")

        with open(MAIN_CHECKSUM_PATH, "r", encoding="utf8") as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 7)
            self.assertTrue(HEADER_LINE in lines)
            self.assertTrue(TEST1_LINE in lines)

        num_lines_removed = remove_missing_checksums(TESTFILES_PATH, False, False)
        self.assertEqual(num_lines_removed, 1)

        with open(MAIN_CHECKSUM_PATH, "r", encoding="utf8") as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 6)
            self.assertTrue(HEADER_LINE in lines)
            self.assertFalse(TEST1_LINE in lines)

    def test_remove_missing_checksums_with_save_orig(self):
        generate_checksums(TESTFILES_PATH, False)
        os.remove(f"{TESTFILES_PATH}/test1.txt")

        with open(MAIN_CHECKSUM_PATH, "r", encoding="utf8") as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 7)
            self.assertTrue(HEADER_LINE in lines)
            self.assertTrue(TEST1_LINE in lines)

        self.assertFalse(os.path.exists(OLD_MAIN_CHECKSUM_PATH))

        num_lines_removed = remove_missing_checksums(TESTFILES_PATH, True, False)
        self.assertEqual(num_lines_removed, 1)

        with open(MAIN_CHECKSUM_PATH, "r", encoding="utf8") as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 6)
            self.assertTrue(HEADER_LINE in lines)
            self.assertFalse(TEST1_LINE in lines)

        self.assertTrue(os.path.exists(OLD_MAIN_CHECKSUM_PATH))

        with open(OLD_MAIN_CHECKSUM_PATH, "r", encoding="utf8") as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 7)
            self.assertTrue(HEADER_LINE in lines)
            self.assertTrue(TEST1_LINE in lines)


class TestChecksumsWithUnsortedSource(unittest.TestCase):
    # for testing generate_checksums using unsorted_source

    @classmethod
    def setUpClass(cls):
        # create folder structure and files to generate checksums for
        if os.path.exists(TESTFILES_PATH):
            shutil.rmtree(TESTFILES_PATH)

        os.makedirs(f"{TESTFILES_PATH}/1")
        os.makedirs(f"{TESTFILES_PATH}/2")
        os.makedirs(f"{TESTFILES_PATH}/1/2")

        with open(f"{TESTFILES_PATH}/test1.txt", "w+", encoding="utf8") as file:
            file.write("1")
        with open(f"{TESTFILES_PATH}/test2.txt", "w+", encoding="utf8") as file:
            file.write("2")
        with open(f"{TESTFILES_PATH}/1/test11.txt", "w+", encoding="utf8") as file:
            file.write("11")
        with open(f"{TESTFILES_PATH}/2/test21.txt", "w+", encoding="utf8") as file:
            file.write("21")
        with open(f"{TESTFILES_PATH}/1/2/test121.txt", "w+", encoding="utf8") as file:
            file.write("121")
        with open(f"{TESTFILES_PATH}/1/2/test122.txt", "w+", encoding="utf8") as file:
            file.write("1")
        with open(f"{TESTFILES_PATH}/1/2/test21.txt", "w+", encoding="utf8") as file:
            file.write("21")
        with open(f"{TESTFILES_PATH}/1/2/test11.txt", "w+", encoding="utf8") as file:
            file.write("112")

        with open(f"{TESTFILES_PATH}/unsorted.txt", "w", encoding="utf8") as file:
            # file.write(CustomMD5Line(TEST1_LINE).md5_line() + '\n')
            file.write("c81e728d9d4c2f636f067f89cc14862d ./test2.txt\n")
            file.write(CustomMD5Line(TEST11_LINE).md5_line + "\n")
            file.write(CustomMD5Line(TEST21_LINE).md5_line + "\n")
            file.write("c4ca4238a0b923820dcc509a6f75849b ./1/nottest1.txt\n")
            # file.write(CustomMD5Line(TEST121_LINE).md5_line() + '\n')
            file.write(CustomMD5Line(TEST122_LINE).md5_line + "\n")
            file.write(CustomMD5Line(TEST21_2_LINE).md5_line + "\n")
            file.write(CustomMD5Line(TEST11_2_LINE).md5_line + "\n")

        with open(
            f"{TESTFILES_PATH}/unsorted_custom.txt", "w", encoding="utf8"
        ) as file:
            file.write(HEADER_LINE)
            # file.write(TEST1_LINE)
            file.write("./test2.txt -> c81e728d9d4c2f636f067f89cc14862d\n")
            file.write(TEST11_LINE)
            file.write(TEST21_LINE)
            file.write("./1/nottest1.txt -> c4ca4238a0b923820dcc509a6f75849b\n")
            # file.write(TEST121_LINE)
            file.write(TEST122_LINE)
            file.write(TEST21_2_LINE)
            file.write(TEST11_2_LINE)

        revert_md5file_to_teracopy_format(
            f"{TESTFILES_PATH}/unsorted_custom.txt",
            f"{TESTFILES_PATH}/unsorted_teracopy.txt",
        )

    @classmethod
    def tearDownClass(cls) -> None:
        # delete created folder and contents
        if os.path.exists(TESTFILES_PATH):
            shutil.rmtree(TESTFILES_PATH)

    def tearDown(self):
        # delete checksum files in testfiles folder
        for root, _, files in os.walk(TESTFILES_PATH):
            for file in files:
                if is_checksum_filename(file, incl_old=True):
                    os.remove(os.path.join(root, file))

    def check_expected_main_checksum_contents(self):
        with open(MAIN_CHECKSUM_PATH, "r", encoding="utf8") as file:
            lines = file.readlines()
            self.assertEqual(len(lines), 8)
            self.assertTrue(HEADER_LINE in lines)
            self.assertTrue(TEST1_LINE in lines)
            self.assertFalse(TEST2_LINE in lines)
            self.assertTrue(
                "./test2.txt -> c81e728d9d4c2f636f067f89cc14862d\n" in lines
            )
            self.assertTrue(TEST11_LINE in lines)
            self.assertTrue(TEST21_LINE in lines)
            self.assertFalse(
                "./1/nottest1.txt -> c4ca4238a0b923820dcc509a6f75849b\n" in lines
            )
            self.assertTrue(TEST121_LINE in lines)
            self.assertTrue(TEST122_LINE in lines)
            self.assertTrue(TEST21_2_LINE in lines)
            self.assertFalse(TEST11_2_LINE in lines)

    def test_correct_checksums_from_unsorted_md5(self):
        generate_checksums(
            TESTFILES_PATH,
            False,
            f"{TESTFILES_PATH}/unsorted.txt",
            "md5",
            ["unsorted.txt", "unsorted_custom.txt", "unsorted_teracopy.txt"],
        )

        self.check_expected_main_checksum_contents()

    def test_correct_checksums_from_unsorted_md5_custom_format(self):
        generate_checksums(
            TESTFILES_PATH,
            False,
            f"{TESTFILES_PATH}/unsorted_custom.txt",
            "custom",
            ["unsorted.txt", "unsorted_custom.txt", "unsorted_teracopy.txt"],
        )

        self.check_expected_main_checksum_contents()

    def test_correct_checksums_from_unsorted_md5_teracopy_format(self):
        generate_checksums(
            TESTFILES_PATH,
            False,
            f"{TESTFILES_PATH}/unsorted_teracopy.txt",
            "teracopy",
            ["unsorted.txt", "unsorted_custom.txt", "unsorted_teracopy.txt"],
        )

        self.check_expected_main_checksum_contents()


class TestVerifyingChecksums(unittest.TestCase):
    # for testing verify_checksums

    @classmethod
    def setUpClass(cls):
        # create folder structure and files to generate checksums for
        if os.path.exists(TESTFILES_PATH):
            shutil.rmtree(TESTFILES_PATH)

        os.makedirs(f"{TESTFILES_PATH}/1")
        os.makedirs(f"{TESTFILES_PATH}/2")
        os.makedirs(f"{TESTFILES_PATH}/1/2")

        with open(f"{TESTFILES_PATH}/test1.txt", "w+", encoding="utf8") as file:
            file.write("1")
        with open(f"{TESTFILES_PATH}/test2.txt", "w+", encoding="utf8") as file:
            file.write("2")
        with open(f"{TESTFILES_PATH}/1/test11.txt", "w+", encoding="utf8") as file:
            file.write("11!")
        with open(f"{TESTFILES_PATH}/2/test21.txt", "w+", encoding="utf8") as file:
            file.write("21")
        with open(f"{TESTFILES_PATH}/1/2/test121.txt", "w+", encoding="utf8") as file:
            file.write("121")
        with open(f"{TESTFILES_PATH}/1/2/test122.txt", "w+", encoding="utf8") as file:
            file.write("1")

        with open(MAIN_CHECKSUM_PATH, "w", encoding="utf8") as file:
            file.write(HEADER_LINE)
            file.write(TEST1_LINE)
            file.write(TEST2_LINE)
            file.write(TEST11_LINE)
            file.write(TEST122_LINE)
            file.write(TEST21_LINE)

    @classmethod
    def tearDownClass(cls) -> None:
        # delete created folder and contents
        if os.path.exists(TESTFILES_PATH):
            shutil.rmtree(TESTFILES_PATH)

    def tearDown(self):
        # delete nested checksum files in testfiles folder
        # WARNING: main checksum files are not deleted between tests
        for root, _, files in os.walk(TESTFILES_PATH):
            for file in files:
                if is_checksum_filename(
                    file, checksum_type="custom_nested", incl_old=True
                ):
                    os.remove(os.path.join(root, file))

    def test_verify_returns_correct_passed_failed_and_new(self):
        passed, failed, new = verify_checksums(TESTFILES_PATH, False, True, False)

        self.assertEqual(len(passed), 4)
        self.assertEqual(len(failed), 1)
        self.assertEqual(len(new), 1)

        self.assertTrue(CustomMD5Line.extract_filepath(TEST1_LINE) in passed)
        self.assertTrue(CustomMD5Line.extract_filepath(TEST2_LINE) in passed)
        self.assertTrue(CustomMD5Line.extract_filepath(TEST11_LINE) in failed)
        self.assertTrue(CustomMD5Line.extract_filepath(TEST121_LINE) in new)
        self.assertTrue(CustomMD5Line.extract_filepath(TEST122_LINE) in passed)
        self.assertTrue(CustomMD5Line.extract_filepath(TEST21_LINE) in passed)

    def test_verify_without_following_nested_dirs_returns_correct_passed_failed_and_new(
        self,
    ):
        passed, failed, new = verify_checksums(TESTFILES_PATH, False, False, False)

        self.assertEqual(len(passed), 2)
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(new), 0)

        self.assertTrue(CustomMD5Line.extract_filepath(TEST1_LINE) in passed)
        self.assertTrue(CustomMD5Line.extract_filepath(TEST2_LINE) in passed)

    def test_verify_with_nested_returns_correct_passed_failed_and_new(self):
        nest_checksums(TESTFILES_PATH, False)
        passed, failed, new = verify_checksums(TESTFILES_PATH, True, True, False)

        self.assertEqual(len(passed), 4)
        self.assertEqual(len(failed), 1)
        self.assertEqual(len(new), 1)

        self.assertTrue(CustomMD5Line.extract_filepath(TEST1_LINE) in passed)
        self.assertTrue(CustomMD5Line.extract_filepath(TEST2_LINE) in passed)
        self.assertTrue(CustomMD5Line.extract_filepath(TEST11_LINE) in failed)
        self.assertTrue(CustomMD5Line.extract_filepath(TEST121_LINE) in new)
        self.assertTrue(CustomMD5Line.extract_filepath(TEST122_LINE) in passed)
        self.assertTrue(CustomMD5Line.extract_filepath(TEST21_LINE) in passed)

    def test_verify_with_nested_without_following_nested_dirs_returns_correct_passed_failed_and_new(
        self,
    ):
        # also tests missing main_checksum file does not matter when use_nested_checksums
        nest_checksums(TESTFILES_PATH, False)
        passed, failed, new = verify_checksums(
            f"{TESTFILES_PATH}/1/2", True, False, False
        )

        self.assertEqual(len(passed), 1)
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(new), 1)

        self.assertTrue(CustomMD5Line.extract_filepath(TEST121_LINE, "2") in new)
        self.assertTrue(CustomMD5Line.extract_filepath(TEST122_LINE, "2") in passed)

    def test_verify_with_nested_but_missing_nested_checksums(self):
        # also tests main_checksum ignored when use_nested_checksums
        passed, failed, new = verify_checksums(TESTFILES_PATH, True, False, False)

        # all files should be in list of 'new' files
        self.assertEqual(len(passed), 0)
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(new), 2)

        self.assertTrue(CustomMD5Line.extract_filepath(TEST1_LINE) in new)
        self.assertTrue(CustomMD5Line.extract_filepath(TEST2_LINE) in new)

    def test_verify_without_nested_and_missing_checksum_file_returns_empty_lists(self):
        passed, failed, new = verify_checksums(
            f"{TESTFILES_PATH}/1/2", False, False, False
        )

        self.assertEqual(len(passed), 0)
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(new), 0)
