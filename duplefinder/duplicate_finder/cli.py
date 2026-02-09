#!/usr/bin/env python3
"""
CLI interface for duplicate file finder
"""

import os
import sys
import argparse

from .core import (
    find_duplicates,
    delete_duplicates,
    get_duplicates_report,
    format_size,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Find duplicate files in a directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  duplicate-finder /path/to/directory
  duplicate-finder /path/to/directory -r false
  duplicate-finder /path/to/directory --min-size 1024
  duplicate-finder /path/to/directory --show-size
  duplicate-finder /path/to/directory --dry-run
  duplicate-finder /path/to/directory --delete
        """
    )

    parser.add_argument(
        "directory",
        help="Directory to scan for duplicates"
    )
    parser.add_argument(
        "-r", "--recursive",
        type=lambda x: x.lower() == 'true',
        default=True,
        help="Search subdirectories (default: true)"
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=1,
        help="Minimum file size in bytes (default: 1)"
    )
    parser.add_argument(
        "--show-size",
        action="store_true",
        help="Show file sizes"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete duplicate files (keeps first occurrence)"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress output"
    )

    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    """Validate command line arguments"""
    if not os.path.isdir(args.directory):
        raise ValueError(f"'{args.directory}' is not a valid directory")

    if args.delete and args.dry_run:
        raise ValueError("Cannot use both --delete and --dry-run")

    if args.min_size < 0:
        raise ValueError("Minimum size must be non-negative")


def progress_callback(processed: int, total: int) -> None:
    """Display progress updates"""
    print(f"Processed {processed} of {total} files...", end='\r', file=sys.stderr)


def main() -> None:
    """Main CLI entry point"""
    try:
        args = parse_args()
        validate_args(args)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Display scan information
    if not args.quiet:
        print(f"Scanning directory: {args.directory}", file=sys.stderr)
        print(f"Recursive: {args.recursive}, Min size: {args.min_size} bytes", file=sys.stderr)

    try:
        # Find duplicates
        duplicates = find_duplicates(
            args.directory,
            recursive=args.recursive,
            min_size=args.min_size,
            progress_callback=progress_callback if not args.quiet else None
        )

        # Display results
        report = get_duplicates_report(duplicates, show_size=args.show_size)
        print(report)

        # Handle deletion
        if args.dry_run:
            total_sets = len(duplicates)
            total_space = sum(
                paths[0].stat().st_size * (len(paths) - 1)
                for paths in duplicates.values()
            )
            print(f"\nDry run: Would delete {len(duplicates)} duplicate sets")
            print(f"Would free approximately {format_size(total_space)}")

        elif args.delete and duplicates:
            if not args.quiet:
                print("\nDeleting duplicate files...", file=sys.stderr)

            deleted_count, freed_space = delete_duplicates(duplicates)

            if not args.quiet:
                print(f"Deleted {deleted_count} files, freed {format_size(freed_space)}", file=sys.stderr)

    except KeyboardInterrupt:
        if not args.quiet:
            print("\n\nOperation cancelled by user", file=sys.stderr)
        sys.exit(130)

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()