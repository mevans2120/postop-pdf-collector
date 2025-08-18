"""Setup script for PostOp PDF Collector."""

from pathlib import Path

from setuptools import find_packages, setup

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    with open(requirements_path) as f:
        requirements = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#") and not line.startswith("-")
        ]

setup(
    name="postop-pdf-collector",
    version="1.0.0",
    author="Michael Evans",
    author_email="",
    description="A comprehensive system for collecting and analyzing post-operative instruction PDFs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/michaelevans/postop-pdf-collector",
    packages=find_packages(exclude=["tests", "tests.*", "docs", "docs.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Healthcare Industry",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
            "isort>=5.12.0",
        ],
        "ocr": [
            "pytesseract>=0.3.10",
            "pillow>=10.0.0",
        ],
        "advanced": [
            "pandas>=2.0.0",
            "sqlalchemy>=2.0.0",
            "redis>=5.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "postop-collector=postop_collector.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)