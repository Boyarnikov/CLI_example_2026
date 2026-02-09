"""
Duplicate File Finder - A CLI utility to find duplicate files in a directory
"""

__version__ = "1.0.0"
__author__ = "Ilya Boyarnikov"
__description__ = "A tool to find and manage duplicate files"

from .core import (
    calculate_file_hash,
    find_duplicates,
    format_size,
    analyze_duplicates,
    delete_duplicates,
    get_duplicates_report,
)