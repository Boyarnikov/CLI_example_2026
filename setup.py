from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="calculator-cli",
    version="1.0.0",
    author="Your Name",
    description="A command-line calculator library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/calculator-cli",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "calc=calculator_cli.cli:main",
        ],
    },
    install_requires=[
        # List your dependencies here
    ],
)