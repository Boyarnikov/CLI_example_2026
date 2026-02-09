"""
Core functionality for finding duplicate files
"""

import hashlib
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


def calculate_file_hash(filepath: Path, chunk_size: int = 8192) -> Optional[str]:
    """
    Calculate MD5 hash of a file

    Args:
        filepath: Path to the file
        chunk_size: Size of chunks to read at once

    Returns:
        MD5 hash string or None if file cannot be read
    """
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except (IOError, OSError, PermissionError):
        return None


def find_duplicates(
        directory: str,
        recursive: bool = True,
        min_size: int = 1,
        progress_callback=None
) -> Dict[str, List[Path]]:
    """
    Find duplicate files in a directory

    Args:
        directory: Path to search
        recursive: Whether to search subdirectories
        min_size: Minimum file size in bytes to consider
        progress_callback: Callback function for progress updates

    Returns:
        Dictionary with file hashes as keys and lists of file paths as values
    """
    duplicates = defaultdict(list)
    total_files = 0
    processed_files = 0

    # Walk through directory
    for root, dirs, files in os.walk(directory):
        for filename in files:
            filepath = Path(root) / filename
            total_files += 1

            # Check file size
            try:
                file_size = filepath.stat().st_size
                if file_size < min_size:
                    continue
            except OSError:
                continue

            # Calculate hash
            file_hash = calculate_file_hash(filepath)
            if file_hash:
                duplicates[file_hash].append(filepath)
                processed_files += 1

            # Call progress callback if provided
            if progress_callback and processed_files % 100 == 0:
                progress_callback(processed_files, total_files)

        if not recursive:
            break

    # Filter to only show actual duplicates
    return {h: paths for h, paths in duplicates.items() if len(paths) > 1}


def format_size(size_bytes: int) -> str:
    """
    Convert bytes to human-readable format

    Args:
        size_bytes: Size in bytes

    Returns:
        Human readable size string
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def analyze_duplicates(duplicates: Dict[str, List[Path]]) -> Tuple[int, int]:
    """
    Analyze duplicates to get statistics

    Args:
        duplicates: Dictionary of duplicate files

    Returns:
        Tuple of (total_duplicate_sets, total_reclaimable_space)
    """
    total_sets = len(duplicates)
    total_space = 0

    for file_hash, filepaths in duplicates.items():
        try:
            file_size = filepaths[0].stat().st_size
            total_space += file_size * (len(filepaths) - 1)
        except OSError:
            continue

    return total_sets, total_space


def delete_duplicates(duplicates: Dict[str, List[Path]]) -> Tuple[int, int]:
    """
    Delete duplicate files (keep first one in each set)

    Args:
        duplicates: Dictionary of duplicate files

    Returns:
        Tuple of (deleted_count, freed_space)
    """
    deleted_count = 0
    freed_space = 0

    for file_hash, filepaths in duplicates.items():
        try:
            file_size = filepaths[0].stat().st_size
            # Keep first file, delete the rest
            for filepath in filepaths[1:]:
                try:
                    filepath.unlink()
                    deleted_count += 1
                    freed_space += file_size
                except OSError as e:
                    print(f"Error deleting {filepath}: {e}")
        except (OSError, IndexError):
            continue

    return deleted_count, freed_space


def get_duplicates_report(
        duplicates: Dict[str, List[Path]],
        show_size: bool = False
) -> str:
    """
    Generate a formatted report of duplicate files

    Args:
        duplicates: Dictionary of duplicate files
        show_size: Whether to include file sizes

    Returns:
        Formatted report string
    """
    if not duplicates:
        return "No duplicate files found!\n"

    total_sets, total_space = analyze_duplicates(duplicates)

    report_lines = [f"Found {total_sets} sets of duplicates:", "-" * 60]

    for i, (file_hash, filepaths) in enumerate(duplicates.items(), 1):
        try:
            file_size = filepaths[0].stat().st_size
            size_info = f" ({format_size(file_size)})" if show_size else ""
            report_lines.append(f"\nSet {i} - Hash: {file_hash[:8]}...{size_info}")
            report_lines.append("Files:")

            for j, filepath in enumerate(filepaths):
                prefix = "[KEEP]   " if j == 0 else "[DUPLICATE]"
                report_lines.append(f"  {prefix} {filepath}")
        except OSError:
            continue

    if total_space > 0:
        report_lines.append(f"\nTotal reclaimable space: {format_size(total_space)}")

    return "\n".join(report_lines)