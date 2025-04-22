# src/reposcribe/core.py

import os
import sys
from typing import List, Tuple

import pathspec  # For ignore-pattern matching

# --- Default Ignore Patterns ---
# Covers common unwanted files, directories, and binaries
DEFAULT_IGNORE_PATTERNS = [
    # Version control metadata
    ".git/", ".hg/", ".svn/", ".bzr/",
    # Built-in ignore files
    ".gitignore", ".reposcribe_ignore",

    # Dependency lock files
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "Pipfile.lock", "composer.lock",
    "Gemfile.lock", "Cargo.lock", "go.sum",

    # Compiled code / binaries
    "*.pyc", "__pycache__", "*.class", "*.jar", "*.war",
    "*.o", "*.a", "*.so", "*.dll", "*.exe",

    # Build / dist directories
    "build/", "dist/", "target/", "bin/", "obj/", "out/",
    "public/build/",

    # Framework/cache directories
    ".next/", ".nuxt/", ".svelte-kit/", ".vercel/",
    ".serverless/", ".terraform/",

    # Environment files
    ".env", ".env.*",

    # Virtual environments
    ".venv/", "venv/", "env/",

    # IDE/editor
    ".idea/", ".vscode/", "*.sublime-*",
    ".project", ".settings/", ".classpath",
    "*.swp", "*.swo",

    # OS metadata
    ".DS_Store", "Thumbs.db",

    # Logs
    "*.log",

    # Test outputs
    "coverage/", ".coverage", "htmlcov/", "*.lcov",
    "nosetests.xml", "pytest.xml", ".pytest_cache/",

    # Media/assets/binaries
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp", "*.svg",
    "*.mp3", "*.wav", "*.ogg", "*.mp4", "*.avi",
    "*.mov", "*.mkv", "*.webm", "*.pdf", "*.docx", "*.pptx",
    "*.zip", "*.tar", "*.gz", "*.rar", "*.7z",

    # Dependency directories
    "node_modules/", "vendor/", "bower_components/",

    # Cloud artifacts
    "cdk.out/",
]


def read_ignore_patterns(ignore_file_paths: List[str]) -> List[str]:
    """
    Read multiple ignore files (like .gitignore and .reposcribe_ignore),
    merge their non-comment lines with DEFAULT_IGNORE_PATTERNS,
    and return the combined list of patterns.
    """
    patterns = DEFAULT_IGNORE_PATTERNS.copy()
    for path in ignore_file_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    lines = [
                        line.strip()
                        for line in f.read().splitlines()
                        if line.strip() and not line.strip().startswith("#")
                    ]
                if lines:
                    patterns.extend(lines)
                    print(f"Read patterns from {path}", file=sys.stderr)
                else:
                    print(
                        f"Ignore file exists but empty: {path}", file=sys.stderr)
            except Exception as e:
                print(f"Warning: failed to read {path}: {e}", file=sys.stderr)
        else:
            print(f"No ignore file at {path}", file=sys.stderr)
    return patterns


def generate_file_tree(file_paths: List[str]) -> str:
    """
    Generate a visual tree representation of file_paths (POSIX-style).
    """
    if not file_paths:
        return "(No files found to include in tree)\n"

    tree_lines = ["Exported File Structure:", "."]
    tree_dict = {}
    for rel in file_paths:
        parts = rel.split("/")
        node = tree_dict
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                node.setdefault(part, None)
            else:
                node = node.setdefault(part, {})

    def _format(node, prefix=""):
        entries = sorted(node.items())
        for idx, (name, child) in enumerate(entries):
            is_last = idx == len(entries) - 1
            connector = "└── " if is_last else "├── "
            tree_lines.append(f"{prefix}{connector}{name}")
            if isinstance(child, dict):
                extension = "    " if is_last else "│   "
                _format(child, prefix + extension)

    _format(tree_dict)
    return "\n".join(tree_lines) + "\n"


def find_exportable_files(project_root: str, spec: pathspec.PathSpec) -> List[str]:
    """
    Walk project_root, prune directories matching spec,
    and collect files not matching spec.
    Returns a sorted list of POSIX-style relative paths.
    """
    files = []
    for dirpath, dirnames, filenames in os.walk(project_root, topdown=True):
        rel_dir = os.path.relpath(dirpath, project_root)
        if rel_dir == ".":
            rel_dir = ""

        # prune ignored directories
        pruned = []
        for d in dirnames:
            candidate = os.path.join(rel_dir, d).replace(os.sep, "/") + "/"
            if spec.match_file(candidate):
                pruned.append(d)
        dirnames[:] = [d for d in dirnames if d not in pruned]

        for fname in filenames:
            rel_file = os.path.join(rel_dir, fname).replace(os.sep, "/")
            if not spec.match_file(rel_file):
                files.append(rel_file)

    return sorted(files)


def write_export_file(
    output_path: str,
    project_root: str,
    files: List[str],
    encoding: str,
    errors: str,
    include_tree: bool,
) -> Tuple[int, int]:
    """
    Write optional file tree and then each file's contents to output_path.
    Returns (file_count, total_bytes).
    """
    count = 0
    total_bytes = 0
    with open(output_path, "w", encoding=encoding) as out:
        if include_tree:
            tree = generate_file_tree(files)
            out.write("--- START FILE TREE ---\n")
            out.write(tree)
            out.write("--- END FILE TREE ---\n\n")

        for rel in files:
            full = os.path.join(project_root, rel.replace("/", os.sep))
            print(f"Scribing: {rel}", file=sys.stderr)
            out.write(f"--- START FILE: {rel} ---\n")
            try:
                with open(full, "r", encoding=encoding, errors=errors) as f:
                    data = f.read()
                out.write(data)
                count += 1
                total_bytes += len(data.encode(encoding, errors=errors))
            except Exception as e:
                msg = f"Error reading file: {e}"
                out.write(msg + "\n")
                print(f"Warning: {rel} read failed: {e}", file=sys.stderr)
            out.write(f"\n--- END FILE: {rel} ---\n\n")

    return count, total_bytes
