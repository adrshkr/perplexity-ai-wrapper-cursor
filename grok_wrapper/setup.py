"""
Setup script for Grok Chat API Wrapper
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ""

setup(
    name="grok-wrapper",
    version="1.0.0",
    description="Terminal interface for Grok chat with automatic authentication",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Grok Wrapper",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "playwright>=1.40.0",
    ],
    entry_points={
        "console_scripts": [
            "grok=src.interfaces.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)

