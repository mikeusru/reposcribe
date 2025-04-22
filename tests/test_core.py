import os
import sys
from pathlib import Path

import pathspec
import pytest

# Functions to test
from reposcribe.core import (find_exportable_files, generate_file_tree,
                             read_ignore_patterns, write_export_file)


# --- Helper to create mock file system ---
# (Still necessary for find/write tests)
def create_mock_fs(base_path: Path, structure: dict, gitignore_content: str = None, reposcribe_content: str = None):
    """Creates a mock file system structure under base_path."""
    # Write .gitignore if provided
    if gitignore_content is not None:
        (base_path / ".gitignore").write_text(gitignore_content, encoding="utf-8")
    # Write .reposcribe_ignore if provided
    if reposcribe_content is not None:
        (base_path / ".reposcribe_ignore").write_text(reposcribe_content, encoding="utf-8")
    # Always create a .git directory
    git_dir = base_path / ".git"
    if not git_dir.exists():
        git_dir.mkdir()
        (git_dir / "config").write_text("git stuff", encoding="utf-8")
    # Create files/dirs
    for name, content in structure.items():
        path = base_path / name
        if isinstance(content, dict):
            path.mkdir(exist_ok=True)
            create_mock_fs(path, content)
        elif isinstance(content, str):
            path.write_text(content, encoding="utf-8")

# --- Test reading ignore patterns ---


def test_read_ignore_patterns_single_file(tmp_path):
    content = "# Comment\n*.log\n\nbuild/"
    gitignore_path = tmp_path / ".gitignore"
    gitignore_path.write_text(content, encoding="utf-8")

    lines = read_ignore_patterns([str(gitignore_path)])

    # Patterns from .gitignore should appear
    assert "*.log" in lines
    assert "build/" in lines
    # Default patterns still included
    assert ".git/" in lines
    assert "*.pyc" in lines
    assert "node_modules/" in lines


def test_read_ignore_patterns_multiple_files(tmp_path):
    gitignore_content = "# Git ignore\n*.log\nbuild/"
    reposcribe_content = "# RS ignore\ntests/\n*.tmp"

    gitignore_path = tmp_path / ".gitignore"
    reposcribe_path = tmp_path / ".reposcribe_ignore"
    gitignore_path.write_text(gitignore_content, encoding="utf-8")
    reposcribe_path.write_text(reposcribe_content, encoding="utf-8")

    lines = read_ignore_patterns([str(gitignore_path), str(reposcribe_path)])

    # Patterns from both files
    assert "*.log" in lines
    assert "build/" in lines
    assert "tests/" in lines
    assert "*.tmp" in lines
    # Default patterns
    assert ".git/" in lines
    assert "*.png" in lines


def test_read_ignore_patterns_missing_file(tmp_path):
    gitignore_content = "# Git ignore\n*.log\nbuild/"
    gitignore_path = tmp_path / ".gitignore"
    gitignore_path.write_text(gitignore_content, encoding="utf-8")

    missing = tmp_path / "noignore"
    lines = read_ignore_patterns([str(gitignore_path), str(missing)])

    assert "*.log" in lines
    assert "build/" in lines
    assert ".git/" in lines


def test_read_ignore_patterns_empty_files(tmp_path):
    gitignore_path = tmp_path / ".gitignore"
    reposcribe_path = tmp_path / ".reposcribe_ignore"

    gitignore_path.write_text("", encoding="utf-8")
    reposcribe_path.write_text("# just comments", encoding="utf-8")

    lines = read_ignore_patterns([str(gitignore_path), str(reposcribe_path)])
    # Should still contain defaults
    assert ".git/" in lines
    assert "*.png" in lines

# --- Integration with PathSpec ---


def test_integration_with_pathspec(tmp_path):
    gitignore_content = "*.log\nbuild/"
    reposcribe_content = "tests/\n*.tmp"

    structure = {
        "main.py": "print('hi')",
        "README.md": "# Title",
        "app.log": "logdata",
        "temp.tmp": "tmpdata",
        "build": {"out.bin": "bin"},
        "tests": {"test_app.py": "def test(): pass"},
        "src": {"mod.py": "code"},
    }
    create_mock_fs(tmp_path, structure, gitignore_content, reposcribe_content)

    ignore_files = [str(tmp_path / ".gitignore"),
                    str(tmp_path / ".reposcribe_ignore")]
    patterns = read_ignore_patterns(ignore_files)
    spec = pathspec.PathSpec.from_lines(
        pathspec.patterns.GitWildMatchPattern, patterns)
    found = find_exportable_files(str(tmp_path), spec)

    expected = ["README.md", "main.py", "src/mod.py"]
    assert sorted(found) == sorted(expected)
    # Ensure ignored entries are absent
    for bad in ["app.log", "temp.tmp", "build/out.bin", "tests/test_app.py"]:
        assert bad not in found

# --- File Tree generation ---


def test_generate_file_tree_empty():
    assert generate_file_tree([]) == "(No files found to include in tree)\n"


def test_generate_file_tree_simple():
    files = ["README.md", "src/app.py"]
    expected = (
        "Exported File Structure:\n"
        ".\n"
        "├── README.md\n"
        "└── src\n"
        "    └── app.py\n"
    )
    assert generate_file_tree(files) == expected

# --- find_exportable_files basic ignore (defaults + single .gitignore) ---


def test_find_files_basic_ignore(tmp_path):
    structure = {
        "a.py": "x=1",
        "b.log": "log",
        ".env": "X=Y",
        "img.png": "img",
        "build": {"f.txt": "f"},
        "pkg": {"mod.py": "code"},
    }
    gitignore = "*.log\nbuild/"
    create_mock_fs(tmp_path, structure, gitignore)
    patterns = read_ignore_patterns([str(tmp_path / ".gitignore")])
    spec = pathspec.PathSpec.from_lines(
        pathspec.patterns.GitWildMatchPattern, patterns)
    found = find_exportable_files(str(tmp_path), spec)
    assert sorted(found) == sorted(["a.py", "pkg/mod.py"])

# --- write_export_file ---


def test_write_export_file_with_tree(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    structure = {"f1.txt": "Hello", "d": {"f2.md": "World"}}
    create_mock_fs(root, structure)
    files = ["f1.txt", "d/f2.md"]
    out = tmp_path / "out.txt"

    count, size = write_export_file(
        str(out), str(root), files, "utf-8", "ignore", True)
    assert out.exists()
    assert count == 2
    text = out.read_text(encoding="utf-8")
    assert "--- START FILE TREE ---" in text
    # Tree entries may be sorted alphabetically: 'd' first, then 'f1.txt'
    assert "├── d" in text
    assert "└── f1.txt" in text
    # f2.md should appear under 'd' with vertical bar indent
    assert "│   └── f2.md" in text
    assert "Hello" in text and "World" in text


def test_write_export_file_missing(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    create_mock_fs(root, {"ok.txt": "yes"})
    files = ["ok.txt", "no.txt"]
    out = tmp_path / "out.txt"
    count, size = write_export_file(str(out), str(
        root), files, "utf-8", "ignore", False)
    assert count == 1
    content = out.read_text(encoding="utf-8")
    assert "ok.txt" in content and "yes" in content
    assert "no.txt" in content and "Error reading file:" in content
