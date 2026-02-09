from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="duplicate-finder",
    version="1.0.0",
    author="Ilya Boyarnikov",
    author_email="iboyarnikov@gmail.com",
    description="A CLI tool to find and manage duplicate files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Boyarnikov/CLI_example_2026",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Topic :: System :: Filesystems",
        "Topic :: Utilities",
    ],
    python_requires=">=3.7",
    install_requires=[],
    entry_points={
        "console_scripts": [
            "duplicate-finder=duplicate_finder.cli:main",
        ],
    },
    keywords="duplicate files finder cli utility",
    project_urls={
        "Bug Reports": "https://github.com/Boyarnikov/CLI_example_2026/issues",
        "Source": "https://github.com/Boyarnikov/CLI_example_2026/",
    },
)