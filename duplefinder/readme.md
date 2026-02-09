# Simple dupe file finder

NOTE: this is a part of an example project to showcase CLI usages for my students. **THIS IS NOT RECOMMENDED FOR PRODUCTION USE!**

A command-line utility to find and manage duplicate files in directories.

## Installation

### From Source

1. Clone or download the repository
2. Navigate to the project directory
3. Install the package:

```bash
pip install .
```

Usage: 
- Find duplicates in current directory

```duplicate-finder .```

- Find duplicates in specific directory

```duplicate-finder /path/to/directory```

- Non-recursive search

```duplicate-finder /path/to/directory -r false```

- Only consider files larger than 1KB

```duplicate-finder /path/to/directory --min-size 1024```

- Show file sizes

```duplicate-finder /path/to/directory --show-size```

- Dry run - show what would be deleted

```duplicate-finder /path/to/directory --dry-run```

- Actually delete duplicates (keeps first file in each set)

```duplicate-finder /path/to/directory --delete```