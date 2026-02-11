import unittest
import tempfile
import os
import shutil
import subprocess
import sys
import re
import time
from pathlib import Path


class TestDuplicateFinderCLI(unittest.TestCase):

    def setUp(self):
        self.test_root = Path(tempfile.mkdtemp(prefix="dupefinder_test_"))
        self.create_test_scenarios()
        self.script_path = "duplicate-finder"

    def tearDown(self):
        shutil.rmtree(self.test_root, ignore_errors=True)

    def create_test_scenarios(self):
        # Simple duplicates
        self.simple_dir = self.test_root / "01_simple"
        self.simple_dir.mkdir()
        for i in range(3):
            (self.simple_dir / f"file{i}.txt").write_text("SIMPLE_DUPLICATE")

        # Nested duplicates
        self.nested_dir = self.test_root / "02_nested"
        self.nested_dir.mkdir()
        (self.nested_dir / "main.txt").write_text("NESTED_DUPLICATE")

        backup_dir = self.nested_dir / "backup"
        backup_dir.mkdir()
        (backup_dir / "copy.txt").write_text("NESTED_DUPLICATE")

        archive_dir = self.nested_dir / "archive"
        archive_dir.mkdir()
        (archive_dir / "archive.txt").write_text("NESTED_DUPLICATE")

        # Size filter test
        self.size_dir = self.test_root / "03_size_filter"
        self.size_dir.mkdir()
        for i in range(2):
            (self.size_dir / f"small{i}.txt").write_text("SMALL")
        for i in range(2):
            (self.size_dir / f"large{i}.txt").write_text("LARGE" * 100)

        # Empty files
        self.empty_dir = self.test_root / "04_empty"
        self.empty_dir.mkdir()
        for i in range(3):
            (self.empty_dir / f"empty{i}.txt").touch()

        # Unique files only
        self.unique_dir = self.test_root / "05_unique"
        self.unique_dir.mkdir()
        for i in range(3):
            (self.unique_dir / f"unique{i}.txt").write_text(f"UNIQUE_CONTENT_{i}")

        # Delete test
        self.delete_dir = self.test_root / "06_delete_test"
        self.delete_dir.mkdir()
        for i in range(3):
            (self.delete_dir / f"delete_me_{i}.txt").write_text("DELETE_TEST")

        # Mixed duplicates and unique
        self.mixed_dir = self.test_root / "07_mixed"
        self.mixed_dir.mkdir()
        for i in range(2):
            (self.mixed_dir / f"dupe{i}.txt").write_text("DUPLICATE_CONTENT")
        (self.mixed_dir / "unique1.txt").write_text("UNIQUE_1")
        (self.mixed_dir / "unique2.txt").write_text("UNIQUE_2")

        # Special characters
        self.special_dir = self.test_root / "08_special_chars"
        self.special_dir.mkdir()
        (self.special_dir / "test!@#$%^&.txt").write_text("SPECIAL")
        (self.special_dir / "copy!@#$%^&.txt").write_text("SPECIAL")

    def run_dupefinder(self, *args):
        cmd = [self.script_path] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result

    def normalize_paths(self, text):
        if isinstance(text, str):
            return text.replace('\\', '/')
        return text

    def assertInOutput(self, expected, output):
        normalized_output = self.normalize_paths(output)
        normalized_expected = self.normalize_paths(expected)
        self.assertIn(normalized_expected, normalized_output)

    def test_simple_duplicates(self):
        result = self.run_dupefinder(str(self.simple_dir))
        self.assertEqual(result.returncode, 0)
        self.assertInOutput("Found 1 sets of duplicates", result.stdout)
        for i in range(3):
            self.assertInOutput(f"file{i}.txt", result.stdout)

    def test_nested_duplicates(self):
        result = self.run_dupefinder(str(self.nested_dir), "-r", "true")
        self.assertEqual(result.returncode, 0)
        self.assertInOutput("Found 1 sets of duplicates", result.stdout)

        normalized_output = self.normalize_paths(result.stdout)
        self.assertIn("main.txt", normalized_output)
        self.assertIn("backup/copy.txt", normalized_output)
        self.assertIn("archive/archive.txt", normalized_output)

    def test_non_recursive(self):
        result = self.run_dupefinder(str(self.nested_dir), "-r", "false")
        self.assertEqual(result.returncode, 0)
        self.assertInOutput("No duplicate files found", result.stdout)

    def test_min_size_filter(self):
        result = self.run_dupefinder(str(self.size_dir), "--min-size", "100")
        self.assertEqual(result.returncode, 0)
        self.assertInOutput("Found 1 sets of duplicates", result.stdout)

        normalized_output = self.normalize_paths(result.stdout)
        self.assertIn("large0.txt", normalized_output)
        self.assertIn("large1.txt", normalized_output)
        self.assertNotIn("small", normalized_output)

    def test_show_size(self):
        result = self.run_dupefinder(str(self.simple_dir), "--show-size")
        self.assertEqual(result.returncode, 0)

        size_pattern = r'\d+\.\d+\s+[KMG]?B'
        self.assertTrue(re.search(size_pattern, result.stdout))

    def test_empty_files(self):
        result = self.run_dupefinder(str(self.empty_dir), "--min-size", "0")
        self.assertEqual(result.returncode, 0)
        self.assertInOutput("Found 1 sets of duplicates", result.stdout)

        # Size is only shown with --show-size flag
        result_with_size = self.run_dupefinder(str(self.empty_dir), "--min-size", "0", "--show-size")
        self.assertInOutput("0.0 B", result_with_size.stdout)

    def test_dry_run(self):
        result = self.run_dupefinder(str(self.delete_dir), "--dry-run")
        self.assertEqual(result.returncode, 0)
        self.assertInOutput("Dry run:", result.stdout)
        self.assertInOutput("Would delete", result.stdout)
        self.assertTrue((self.delete_dir / "delete_me_1.txt").exists())

    def test_delete_duplicates(self):
        delete_test = self.test_root / "delete_test_specific"
        delete_test.mkdir()

        try:
            for i in range(2):
                (delete_test / f"test_{i}.txt").write_text("DELETE_ME")

            files_before = len(list(delete_test.glob("*.txt")))
            result = self.run_dupefinder(str(delete_test), "--delete")

            self.assertEqual(result.returncode, 0)
            files_after = len(list(delete_test.glob("*.txt")))

            self.assertEqual(files_after, files_before - 1)
            self.assertTrue((delete_test / "test_0.txt").exists())
            self.assertFalse((delete_test / "test_1.txt").exists())

        finally:
            if delete_test.exists():
                shutil.rmtree(delete_test)

    def test_quiet_mode(self):
        result = self.run_dupefinder(str(self.simple_dir), "--quiet")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr.strip(), "")
        self.assertInOutput("Found 1 sets of duplicates", result.stdout)

    def test_invalid_directory(self):
        invalid_dir = self.test_root / "does_not_exist"
        result = self.run_dupefinder(str(invalid_dir))
        self.assertNotEqual(result.returncode, 0)
        self.assertInOutput("Error", result.stderr)
        self.assertInOutput("not a valid directory", result.stderr)

    def test_delete_and_dry_run_conflict(self):
        result = self.run_dupefinder(str(self.simple_dir), "--delete", "--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertInOutput("Cannot use both --delete and --dry-run", result.stderr)

    def test_no_duplicates(self):
        result = self.run_dupefinder(str(self.unique_dir))
        self.assertEqual(result.returncode, 0)
        self.assertInOutput("No duplicate files found", result.stdout)

    def test_mixed_duplicates_and_unique(self):
        result = self.run_dupefinder(str(self.mixed_dir))
        self.assertEqual(result.returncode, 0)
        self.assertInOutput("Found 1 sets of duplicates", result.stdout)

        normalized_output = self.normalize_paths(result.stdout)
        self.assertIn("dupe0.txt", normalized_output)
        self.assertIn("dupe1.txt", normalized_output)
        self.assertNotIn("unique1.txt", normalized_output)
        self.assertNotIn("unique2.txt", normalized_output)

    def test_special_characters(self):
        result = self.run_dupefinder(str(self.special_dir))
        self.assertEqual(result.returncode, 0)
        self.assertInOutput("Found 1 sets of duplicates", result.stdout)

        normalized_output = self.normalize_paths(result.stdout)
        self.assertIn("test!@#$%^&.txt", normalized_output)
        self.assertIn("copy!@#$%^&.txt", normalized_output)

    def test_very_long_filename(self):
        long_dir = self.test_root / "15_long_filenames"
        long_dir.mkdir()

        try:
            long_name = "x" * 200 + ".txt"
            long_path = long_dir / long_name
            long_path.write_text("LONG")

            duplicate_name = "y" * 200 + ".txt"
            duplicate_path = long_dir / duplicate_name
            duplicate_path.write_text("LONG")

            result = self.run_dupefinder(str(long_dir))
            self.assertEqual(result.returncode, 0)
            self.assertInOutput("Found 1 sets of duplicates", result.stdout)

        finally:
            if long_dir.exists():
                shutil.rmtree(long_dir)

    def test_path_with_spaces(self):
        spaced_dir = self.test_root / "test folder with spaces"
        spaced_dir.mkdir()

        try:
            (spaced_dir / "file1.txt").write_text("SPACES")
            (spaced_dir / "file2.txt").write_text("SPACES")

            result = self.run_dupefinder(str(spaced_dir))
            self.assertEqual(result.returncode, 0)
            self.assertInOutput("Found 1 sets of duplicates", result.stdout)

        finally:
            if spaced_dir.exists():
                shutil.rmtree(spaced_dir)

    """
    @unittest.skipIf((sys.platform == "win32" or sys.platform == "win86") and os.environ.get('CI'),
                     "Unicode path test fails in Windows CI")
    def test_unicode_paths(self):
        unicode_dir = self.test_root / "测试_테스트_тест"
        unicode_dir.mkdir()

        try:
            file1 = unicode_dir / "文件1.txt"
            file1.write_text("UNICODE")
            file2 = unicode_dir / "文件2.txt"
            file2.write_text("UNICODE")

            result = self.run_dupefinder(str(unicode_dir))
            self.assertEqual(result.returncode, 0)
            self.assertInOutput("Found 1 sets of duplicates", result.stdout)

        finally:
            if unicode_dir.exists():
                shutil.rmtree(unicode_dir)
    """

    def test_multiple_duplicate_groups(self):
        multi_dir = self.test_root / "18_multiple_groups"
        multi_dir.mkdir()

        try:
            for i in range(2):
                (multi_dir / f"text_{i}.txt").write_text("TEXT_DUPE")

            for i in range(3):
                (multi_dir / f"binary_{i}.bin").write_bytes(b"\x00\x01\x02")

            for i in range(2):
                (multi_dir / f"empty_{i}.txt").touch()

            result = self.run_dupefinder(str(multi_dir), "--min-size", "0")
            self.assertEqual(result.returncode, 0)

            set_count = len(re.findall(r'Set \d+', result.stdout))
            self.assertEqual(set_count, 3)

        finally:
            if multi_dir.exists():
                shutil.rmtree(multi_dir)


class TestPerformance(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="perf_test_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_performance_many_files(self):
        for i in range(250):
            (self.test_dir / f"set1_{i}.txt").write_text("CONTENT_1")

        for i in range(250):
            (self.test_dir / f"set2_{i}.txt").write_text("CONTENT_2")

        start_time = time.time()
        result = subprocess.run(
            ["duplicate-finder", str(self.test_dir)],
            capture_output=True,
            text=True
        )
        elapsed = time.time() - start_time

        self.assertEqual(result.returncode, 0)
        self.assertIn("Found 2 sets of duplicates", result.stdout)
        self.assertLess(elapsed, 10)


if __name__ == "__main__":
    unittest.main()