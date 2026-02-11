import pytest
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


@pytest.fixture
def temp_dir():
    dir_path = Path(tempfile.mkdtemp())
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def sample_files(temp_dir):
    files = {}

    file1 = temp_dir / "test1.txt"
    file1.write_text("Hello World")
    files['file1'] = file1

    file2 = temp_dir / "test2.txt"
    file2.write_text("Hello World")
    files['file2'] = file2

    file3 = temp_dir / "test3.txt"
    file3.write_text("Different Content")
    files['file3'] = file3

    empty = temp_dir / "empty.txt"
    empty.touch()
    files['empty'] = empty

    return files


@pytest.fixture
def duplicate_scenario(temp_dir):
    for i in range(3):
        (temp_dir / f"dupe_root_{i}.txt").write_text("ROOT_DUPLICATE")

    subdir = temp_dir / "subdir"
    subdir.mkdir()
    for i in range(2):
        (subdir / f"dupe_sub_{i}.txt").write_text("SUBDIR_DUPLICATE")

    (temp_dir / "unique1.txt").write_text("UNIQUE_1")
    (subdir / "unique2.txt").write_text("UNIQUE_2")

    return temp_dir


def test_calculate_hash_same_content(sample_files):
    hash1 = calculate_file_hash(sample_files['file1'])
    hash2 = calculate_file_hash(sample_files['file2'])

    assert hash1 == hash2
    assert len(hash1) == 32


def test_calculate_hash_different_content(sample_files):
    hash1 = calculate_file_hash(sample_files['file1'])
    hash2 = calculate_file_hash(sample_files['file3'])

    assert hash1 != hash2


def test_calculate_hash_empty_file(sample_files):
    hash_value = calculate_file_hash(sample_files['empty'])

    assert hash_value is not None
    assert len(hash_value) == 32
    assert hash_value == "d41d8cd98f00b204e9800998ecf8427e"


def test_calculate_hash_nonexistent_file(temp_dir):
    nonexistent = temp_dir / "does_not_exist.txt"
    hash_value = calculate_file_hash(nonexistent)

    assert hash_value is None


@pytest.mark.parametrize("content,expected_prefix", [
    ("", "d41d8cd9"),
    ("a", "0cc175b9"),
    ("Hello World", "b10a8db1"),
])
def test_calculate_hash_known_values(temp_dir, content, expected_prefix):
    file_path = temp_dir / "test.txt"
    file_path.write_text(content)

    hash_value = calculate_file_hash(file_path)

    assert hash_value.startswith(expected_prefix)


@pytest.mark.parametrize("bytes_input,expected", [
    (0, "0.0 B"),
    (500, "500.0 B"),
    (1023, "1023.0 B"),
    (1024, "1.0 KB"),
    (1536, "1.5 KB"),
    (1048576, "1.0 MB"),
    (1073741824, "1.0 GB"),
    (1099511627776, "1.0 TB"),
])
def test_format_size(bytes_input, expected):
    assert format_size(bytes_input) == expected


def test_find_duplicates_basic(duplicate_scenario):
    duplicates = find_duplicates(str(duplicate_scenario))

    assert len(duplicates) == 2

    group_sizes = [len(paths) for paths in duplicates.values()]
    assert 3 in group_sizes
    assert 2 in group_sizes


def test_find_duplicates_non_recursive(duplicate_scenario):
    duplicates = find_duplicates(str(duplicate_scenario), recursive=False)

    assert len(duplicates) == 1

    for paths in duplicates.values():
        for path in paths:
            assert path.parent == duplicate_scenario


@pytest.mark.parametrize("min_size,expected_groups", [
    (0, 2),
    (1, 2),
    (1000, 0),
])
def test_find_duplicates_min_size(duplicate_scenario, min_size, expected_groups):
    duplicates = find_duplicates(str(duplicate_scenario), min_size=min_size)
    assert len(duplicates) == expected_groups


def test_find_duplicates_with_progress_few_files(tmp_path):
    for i in range(99):
        (tmp_path / f"file_{i}.txt").write_text("content")

    calls = []

    def progress_callback(processed, total):
        calls.append((processed, total))

    find_duplicates(str(tmp_path), progress_callback=progress_callback)

    assert len(calls) == 0


def test_find_duplicates_with_progress_many_files(tmp_path):
    for i in range(150):
        (tmp_path / f"file_{i}.txt").write_text("content")

    calls = []

    def progress_callback(processed, total):
        calls.append((processed, total))

    find_duplicates(str(tmp_path), progress_callback=progress_callback)

    assert len(calls) > 0
    assert calls[0][0] == 100


def test_find_duplicates_with_progress_boundaries(tmp_path):
    test_cases = [
        (99, 0),
        (100, 1),
        (199, 1),
        (200, 2),
    ]

    for file_count, expected_calls in test_cases:
        test_dir = tmp_path / f"test_{file_count}"
        test_dir.mkdir()

        for i in range(file_count):
            (test_dir / f"file_{i}.txt").write_text("content")

        calls = []

        def progress_callback(processed, total):
            calls.append((processed, total))

        find_duplicates(str(test_dir), progress_callback=progress_callback)

        assert len(calls) == expected_calls


def test_find_duplicates_invalid_directory():
    result = find_duplicates("/path/that/does/not/exist")
    assert result == {}


def test_analyze_duplicates(temp_dir):
    files = []
    for i in range(3):
        file_path = temp_dir / f"test_{i}.txt"
        file_path.write_text("X" * 100)
        files.append(file_path)

    duplicates = {"hash1": files}
    total_sets, total_space = analyze_duplicates(duplicates)

    assert total_sets == 1
    assert total_space == 200


def test_delete_duplicates(temp_dir):
    files = []
    for i in range(3):
        file_path = temp_dir / f"delete_{i}.txt"
        file_path.write_text("DELETE_TEST")
        files.append(file_path)

    duplicates = {"hash1": files}

    assert all(f.exists() for f in files)

    deleted_count, freed_space = delete_duplicates(duplicates)

    assert deleted_count == 2
    assert freed_space > 0

    assert files[0].exists()
    assert not files[1].exists()
    assert not files[2].exists()


def test_delete_duplicates_empty_dict():
    deleted_count, freed_space = delete_duplicates({})

    assert deleted_count == 0
    assert freed_space == 0


def test_delete_duplicates_missing_file(temp_dir):
    existing_file = temp_dir / "exists.txt"
    existing_file.write_text("EXISTS")

    nonexistent = temp_dir / "missing.txt"

    duplicates = {
        "hash1": [existing_file, nonexistent]
    }

    deleted_count, freed_space = delete_duplicates(duplicates)

    assert deleted_count == 0


def test_get_duplicates_report_no_duplicates():
    report = get_duplicates_report({})

    assert "No duplicate files found" in report


def test_get_duplicates_report_with_duplicates(temp_dir):
    file1 = temp_dir / "original.txt"
    file2 = temp_dir / "copy.txt"
    file1.write_text("REPORT_TEST")
    file2.write_text("REPORT_TEST")

    duplicates = {"abc123": [file1, file2]}
    report = get_duplicates_report(duplicates)

    assert "Found 1 sets of duplicates" in report
    assert "[KEEP]" in report
    assert "[DUPLICATE]" in report
    assert "original.txt" in report
    assert "copy.txt" in report


def test_get_duplicates_report_with_size(temp_dir):
    file1 = temp_dir / "original.txt"
    file2 = temp_dir / "copy.txt"
    file1.write_text("SIZE_TEST")
    file2.write_text("SIZE_TEST")

    duplicates = {"abc123": [file1, file2]}
    report = get_duplicates_report(duplicates, show_size=True)

    assert "B)" in report
    assert "reclaimable space" in report.lower()


def test_with_pytest_tmpdir(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello")

    hash_value = calculate_file_hash(test_file)

    assert hash_value is not None
    assert len(hash_value) == 32


def test_calculate_file_hash_permission_error(monkeypatch, tmp_path):
    test_file = tmp_path / "secret.txt"
    test_file.write_text("SECRET")

    def mock_open(*args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open)

    hash_value = calculate_file_hash(test_file)
    assert hash_value is None