import unittest
import tempfile
import os
import shutil
from pathlib import Path
from duplicate_finder.core import (
    calculate_file_hash,
    find_duplicates,
    format_size,
    analyze_duplicates,
    delete_duplicates,
    get_duplicates_report,
)


class TestFileHashing(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        tempfile.mktemp()
        self.file1 = Path(self.test_dir) / "test1.txt"
        self.file2 = Path(self.test_dir) / "test2.txt"

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_calculate_hash_same_content(self):
        self.file1.write_text("Hello World")
        self.file2.write_text("Hello World")

        hash1 = calculate_file_hash(self.file1)
        hash2 = calculate_file_hash(self.file2)

        self.assertEqual(hash1, hash2, "Same content should produce same hash")

    def test_calculate_hash_different_content(self):
        self.file1.write_text("Hello World")
        self.file2.write_text("Goodbye World")

        hash1 = calculate_file_hash(self.file1)
        hash2 = calculate_file_hash(self.file2)

        self.assertNotEqual(hash1, hash2, "Different content should produce different hashes")

    def test_calculate_hash_empty_file(self):
        self.file1.touch()

        hash_value = calculate_file_hash(self.file1)
        self.assertIsNotNone(hash_value, "Empty file should produce a hash")
        self.assertEqual(len(hash_value), 32, "MD5 hash should be 32 characters")

    def test_calculate_hash_nonexistent_file(self):
        nonexistent = Path(self.test_dir) / "does_not_exist.txt"
        hash_value = calculate_file_hash(nonexistent)
        self.assertIsNone(hash_value, "Nonexistent file should return None")

    def test_calculate_hash_binary_file(self):
        binary_data = bytes(range(100))
        self.file1.write_bytes(binary_data)

        hash_value = calculate_file_hash(self.file1)
        self.assertIsNotNone(hash_value)
        self.assertEqual(len(hash_value), 32)


class TestFormatSize(unittest.TestCase):
    def test_format_size_bytes(self):
        self.assertEqual(format_size(500), "500.0 B")
        self.assertEqual(format_size(0), "0.0 B")
        self.assertEqual(format_size(1023), "1023.0 B")

    def test_format_size_kilobytes(self):
        self.assertEqual(format_size(1024), "1.0 KB")
        self.assertEqual(format_size(2048), "2.0 KB")
        self.assertEqual(format_size(1536), "1.5 KB")

    def test_format_size_megabytes(self):
        self.assertEqual(format_size(1048576), "1.0 MB")  # 1024*1024
        self.assertEqual(format_size(3145728), "3.0 MB")  # 3*1024*1024

    def test_format_size_gigabytes(self):
        self.assertEqual(format_size(1073741824), "1.0 GB")  # 1024^3
        self.assertEqual(format_size(2147483648), "2.0 GB")

    def test_format_size_terabytes(self):
        tb_size = 1099511627776  # 1024^4
        self.assertEqual(format_size(tb_size), "1.0 TB")


class TestFindDuplicates(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.create_test_files()

    def create_test_files(self):
        for i in range(3):
            file_path = self.test_dir / f"duplicate_group1_{i}.txt"
            file_path.write_text("This is duplicate content")

        for i in range(2):
            file_path = self.test_dir / f"duplicate_group2_{i}.bin"
            file_path.write_bytes(b"\x00\x01\x02\x03")

        for i in range(3):
            file_path = self.test_dir / f"empty_{i}.txt"
            file_path.touch()

        unique_files = [
            ("unique1.txt", "Content A"),
            ("unique2.txt", "Content B"),
            ("unique3.txt", "Content C"),
        ]
        for filename, content in unique_files:
            file_path = self.test_dir / filename
            file_path.write_text(content)

        nested_dir = self.test_dir / "nested"
        nested_dir.mkdir()
        nested_file = nested_dir / "duplicate_group1_nested.txt"
        nested_file.write_text("This is duplicate content")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_find_duplicates_basic(self):
        duplicates = find_duplicates(str(self.test_dir), recursive=True)

        # Should find 2 groups: text duplicates and binary duplicates
        # Empty files are excluded by default (min_size=1)
        self.assertEqual(len(duplicates), 2,
                         "Should find exactly 2 duplicate groups (empty files excluded by default)")

        # Verify group sizes
        group_sizes = [len(paths) for paths in duplicates.values()]
        self.assertIn(4, group_sizes)
        self.assertIn(2, group_sizes)

    def test_find_duplicates_include_empty(self):
        """Test: Should find empty files as duplicates when min_size=0"""
        duplicates = find_duplicates(str(self.test_dir), recursive=True, min_size=0)

        # Should find 3 groups: text, binary, AND empty files
        self.assertEqual(len(duplicates), 3,
                         "Should find exactly 3 duplicate groups when including empty files")

        # Verify empty files are included
        empty_groups = [paths for paths in duplicates.values()
                        if len(paths) == 3 and all(p.stat().st_size == 0 for p in paths)]
        self.assertEqual(len(empty_groups), 1, "Should find one group of empty files")
        self.assertEqual(len(empty_groups[0]), 3, "Empty group should have 3 files")

    def test_find_duplicates_non_recursive(self):
        duplicates = find_duplicates(str(self.test_dir), recursive=False)

        # Should find groups only in root directory
        for file_hash, filepaths in duplicates.items():
            for path in filepaths:
                self.assertNotIn("nested", str(path),
                                 "Non-recursive search shouldn't include nested files")

        text_group_found = False
        for paths in duplicates.values():
            if len(paths) == 3 and all("duplicate_group1" in str(p) for p in paths):
                text_group_found = True
                break
        self.assertTrue(text_group_found, "Should find text group with 3 files in root")

    def test_find_duplicates_min_size_filter(self):
        duplicates = find_duplicates(str(self.test_dir), min_size=100)

        self.assertEqual(len(duplicates), 0,
                         "No duplicates should be found with min_size=100")

        large_file = self.test_dir / "large.txt"
        large_file.write_text("X" * 200)
        duplicate_large = self.test_dir / "large_copy.txt"
        duplicate_large.write_text("X" * 200)

        duplicates = find_duplicates(str(self.test_dir), min_size=100)
        self.assertEqual(len(duplicates), 1,
                         "Should find large file duplicates")

    def test_find_duplicates_with_progress(self):
        self.callback_calls = []

        def progress_callback(processed, total):
            self.callback_calls.append((processed, total))

        duplicates = find_duplicates(
            str(self.test_dir),
            progress_callback=progress_callback
        )

        self.assertEqual(len(self.callback_calls), 0,
                         "Callback should not be called with < 100 files")

    def test_find_duplicates_with_progress_many_files(self):
        many_files_dir = Path(tempfile.mkdtemp())

        try:
            # Create 150 files
            for i in range(150):
                file_path = many_files_dir / f"file_{i}.txt"
                file_path.write_text(f"Content {i % 2}")

            callback_calls = []

            def progress_callback(processed, total):
                callback_calls.append((processed, total))

            duplicates = find_duplicates(
                str(many_files_dir),
                progress_callback=progress_callback
            )

            # Should be called at 100 files
            self.assertEqual(len(callback_calls), 1,
                            "Callback should be called once at 100 files")
            self.assertEqual(callback_calls[0][0], 100,
                            "Should report 100 processed files")
        finally:
            shutil.rmtree(many_files_dir)

    def test_find_duplicates_empty_directory(self):
        empty_dir = self.test_dir / "empty_subdir"
        empty_dir.mkdir()

        duplicates = find_duplicates(str(empty_dir))
        self.assertEqual(len(duplicates), 0, "Empty directory should have no duplicates")

    def test_find_duplicates_no_duplicates(self):
        unique_dir = self.test_dir / "unique_only"
        unique_dir.mkdir()

        # Create all unique files
        for i in range(5):
            (unique_dir / f"unique_{i}.txt").write_text(f"Unique content {i}")

        duplicates = find_duplicates(str(unique_dir))
        self.assertEqual(len(duplicates), 0, "No duplicates should be found")

    def test_find_duplicates_single_file(self):
        single_dir = self.test_dir / "single"
        single_dir.mkdir()

        (single_dir / "only_one.txt").write_text("Alone")

        duplicates = find_duplicates(str(single_dir))
        self.assertEqual(len(duplicates), 0, "Single file cannot be a duplicate")


class TestMinSizeBehavior(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

        # Create empty file (0 bytes)
        self.empty_file = self.test_dir / "empty.txt"
        self.empty_file.touch()
        self.empty_duplicate = self.test_dir / "empty2.txt"
        self.empty_duplicate.touch()

        # Create small file (10 bytes)
        self.small_file = self.test_dir / "small.txt"
        self.small_file.write_text("1234567890")
        self.small_duplicate = self.test_dir / "small2.txt"
        self.small_duplicate.write_text("1234567890")

        # Create larger file (100 bytes)
        self.large_file = self.test_dir / "large.txt"
        self.large_file.write_text("X" * 100)
        self.large_duplicate = self.test_dir / "large2.txt"
        self.large_duplicate.write_text("X" * 100)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_default_min_size_excludes_empty(self):
        duplicates = find_duplicates(str(self.test_dir))

        # Should find small and large duplicates, but not empty
        self.assertEqual(len(duplicates), 2)

        # Verify empty files are not included
        for paths in duplicates.values():
            for path in paths:
                self.assertGreater(path.stat().st_size, 0)

    def test_min_size_zero_includes_empty(self):
        duplicates = find_duplicates(str(self.test_dir), min_size=0)

        # Should find all three duplicate groups
        self.assertEqual(len(duplicates), 3)

        # Verify empty files are included
        empty_groups = [paths for paths in duplicates.values()
                        if any(p.stat().st_size == 0 for p in paths)]
        self.assertEqual(len(empty_groups), 1)

    def test_min_size_threshold(self):
        test_cases = [
            (0, 3),  # Include all
            (1, 2),  # Exclude empty
            (11, 1),  # Exclude empty and small (10 bytes)
            (101, 0),  # Exclude all
        ]

        for min_size, expected_count in test_cases:
            with self.subTest(min_size=min_size):
                duplicates = find_duplicates(str(self.test_dir), min_size=min_size)
                self.assertEqual(len(duplicates), expected_count,
                                 f"With min_size={min_size}, expected {expected_count} groups")


class TestAnalyzeAndDelete(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

        # Create duplicate groups
        self.group1_files = []
        for i in range(3):
            file_path = self.test_dir / f"delete_test_group1_{i}.txt"
            file_path.write_text("Content for deletion test")
            self.group1_files.append(file_path)

        self.group2_files = []
        for i in range(2):
            file_path = self.test_dir / f"delete_test_group2_{i}.txt"
            file_path.write_text("Different content for deletion test")
            self.group2_files.append(file_path)

        # Build duplicates dictionary
        self.duplicates = {
            "hash1": self.group1_files,
            "hash2": self.group2_files,
        }

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_analyze_duplicates(self):
        total_sets, total_space = analyze_duplicates(self.duplicates)

        self.assertEqual(total_sets, 2, "Should have 2 duplicate sets")

        # Calculate expected space
        group1_size = self.group1_files[0].stat().st_size
        group2_size = self.group2_files[0].stat().st_size
        expected_space = group1_size * 2 + group2_size * 1  # Keep 1, delete rest

        self.assertEqual(total_space, expected_space, "Space calculation should be correct")

    def test_delete_duplicates(self):
        # Record files before deletion
        all_files = list(self.test_dir.glob("**/*"))
        initial_count = len(all_files)

        # Perform deletion
        deleted_count, freed_space = delete_duplicates(self.duplicates)

        # Check results
        self.assertEqual(deleted_count, 3, "Should delete 3 files total")
        self.assertEqual(deleted_count, 3, f"Expected 3 deletions, got {deleted_count}")

        # Check which files remain
        remaining_files = list(self.test_dir.glob("**/*"))
        remaining_count = len(remaining_files)
        self.assertEqual(remaining_count, initial_count - 3,
                         f"Should have {initial_count - 3} files left")

        # First file of each group should remain
        self.assertTrue(self.group1_files[0].exists(), "First file of group1 should remain")
        self.assertTrue(self.group2_files[0].exists(), "First file of group2 should remain")

        # Others should be deleted
        self.assertFalse(self.group1_files[1].exists(), "Second file of group1 should be deleted")
        self.assertFalse(self.group1_files[2].exists(), "Third file of group1 should be deleted")
        self.assertFalse(self.group2_files[1].exists(), "Second file of group2 should be deleted")

    def test_delete_duplicates_empty_dict(self):
        deleted_count, freed_space = delete_duplicates({})
        self.assertEqual(deleted_count, 0)
        self.assertEqual(freed_space, 0)


class TestReports(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

        # Create a duplicate set
        self.file1 = self.test_dir / "original.txt"
        self.file2 = self.test_dir / "copy.txt"
        self.file1.write_text("Report test content")
        self.file2.write_text("Report test content")

        self.duplicates = {
            "abc123hash": [self.file1, self.file2]
        }

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_get_duplicates_report_no_duplicates(self):
        report = get_duplicates_report({})
        self.assertIn("No duplicate files found", report)

    def test_get_duplicates_report_with_duplicates(self):
        report = get_duplicates_report(self.duplicates)

        self.assertIn("Found 1 sets of duplicates", report)
        self.assertIn("Set 1", report)
        self.assertIn("[KEEP]", report)
        self.assertIn("[DUPLICATE]", report)
        self.assertIn("original.txt", report)
        self.assertIn("copy.txt", report)

    def test_get_duplicates_report_with_size(self):
        report = get_duplicates_report(self.duplicates, show_size=True)

        self.assertIn("B)", report)  # Size should be shown
        self.assertIn("reclaimable space", report.lower())


if __name__ == "__main__":
    unittest.main()
