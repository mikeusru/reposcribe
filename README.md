# RepoScribe

A command-line tool to scan a project directory, identify files that are not ignored by `.gitignore` rules, and concatenate their contents into a single text file ("scribe" them). It includes a file tree representation at the start of the output, making it ideal for providing context to Large Language Models (LLMs) or for code reviews.

Built with Python, Poetry, Typer, pathspec, and anytree.

## Features

* Includes built-in ignores for common unwanted files (e.g., `.env`, `*.log`, `*.pyc`, `node_modules/`, images, lock files) in addition to your project's `.gitignore`.
* Supports project-specific `.reposcribe_ignore` files for excluding files only from RepoScribe without affecting version control.
* Automatically ignores the `.git` directory.
* Automatically ignores the output file if it resides within the project directory.
* Recursively scans the project directory.
* Prunes ignored directories during scanning for efficiency.
* Includes a file tree representation at the beginning of the output file (can be disabled).
* Prompts user for confirmation with a list of files before writing the output (can be skipped).
* Configurable file encoding and error handling.
* Clear headers/footers in the output file indicating file boundaries.


## Installation

Ensure you have Python (3.12+ recommended) and Poetry installed.

1.  **Clone the repository (or download the source):**
    ```bash
    git clone https://github.com/mikeusru/reposcribe.git
    cd reposcribe
    ```

2.  **Install dependencies using Poetry:**
    ```bash
    poetry install
    ```
    This creates a virtual environment and installs the required libraries.

## Usage

### Option 1: Running from inside the reposcribe project:
```bash
poetry run reposcribe <PROJECT_DIRECTORY> <OUTPUT_FILE> [OPTIONS]
```
### Option 2: Global Installation via pipx

If you’d like to invoke `reposcribe` from anywhere—without activating a virtualenv—use **pipx** to install it into its own isolated environment:

1. **Install pipx** (if you don’t already have it):
   ```bash
   python3 -m pip install --user pipx
   python3 -m pipx ensurepath
   ```
   > After running the above, restart your shell so that `pipx` is on your `PATH`.

2. **Install RepoScribe in editable mode** (from your project root):
   ```bash
   pipx install --editable .
   ```

3. **Run the CLI from any directory**, no `poetry shell` needed:
   ```bash
   reposcribe /path/to/your/dir output.txt
   ```

4. **After making updates** to your code, refresh the pipx install:
   ```bash
   pipx upgrade --editable .
   ```

5. **To uninstall** RepoScribe:
   ```bash
   pipx uninstall reposcribe
   ```

## Ignore Files

RepoScribe respects two types of ignore files:

1. **`.gitignore`**: Standard Git ignore patterns in your project root
2. **`.reposcribe_ignore`**: Optional RepoScribe-specific ignore patterns

The `.reposcribe_ignore` file uses the same pattern format as `.gitignore` but is only used by RepoScribe. This allows you to exclude files from your scribing output without affecting version control.

For example, you might want to include your unit tests in version control but exclude them from your LLM context file to save tokens. You can add this to `.reposcribe_ignore`:

```
# Exclude tests from LLM context
tests/
```

### Arguments:

* `PROJECT_DIRECTORY`: Path to the root directory of the project you want to scribe (must contain .gitignore, if used).
* `OUTPUT_FILE` (Optional): Path to the file where the concatenated content will be saved. If omitted, defaults to `./output/{PROJECT_DIRECTORY_NAME}_context.txt` in the current working directory (the `output` directory will be created if needed).
### Options:

* `--tree / --no-tree`: Include / Do not include a file tree representation (default: --tree).
* `-e, --encoding TEXT`: Encoding to use when reading files (default: utf-8).
* `--errors TEXT`: How to handle file read encoding errors ('ignore', 'replace', 'strict') (default: ignore).
* `-y, --yes`: Skip the confirmation prompt before exporting.
* `--help`: Show the help message and exit.

### Examples:

```bash
# Scribe files from ~/dev/my-project to ~/exports/my-project-context.txt
reposcribe ~/dev/my-project ~/exports/my-project-context.txt

# Scribe files from current directory to output.txt, skipping confirmation and tree
reposcribe . output.txt --yes --no-tree

# If not using `poetry shell`, run via `poetry run`:
poetry run reposcribe ~/dev/my-project ~/exports/my-project-context.txt
```

## Output Format

The output file will contain:

1. **(Optional) File Tree**: A visual representation of the included files' structure (unless `--no-tree` is used).
2. **File Contents**: The contents of all non-ignored files, separated by headers and footers.

Example output:
```markdown
--- START FILE TREE ---
Exported File Structure:
.
├── README.md
└── src
    ├── app.py
    └── utils.py
--- END FILE TREE ---

--- START FILE: README.md ---
# Content of README.md
--- END FILE: README.md ---

--- START FILE: src/app.py ---
# Content of src/app.py
--- END FILE: src/app.py ---
```

## Development

To contribute or modify the tool:

1. Install development dependencies:
    ```bash
    poetry install --with dev
    ```
2. Activate the environment:
    ```bash
    poetry shell
    ```
3. Make your changes in the `src/` directory.
4. Run tests:
    ```bash
    pytest
    ```

## License

Distributed under the MIT License.