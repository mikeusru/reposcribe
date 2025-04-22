import os
import sys
import traceback
from pathlib import Path
from typing import List, Optional

import pathspec
import typer

from .core import (find_exportable_files, read_ignore_patterns,
                   write_export_file)

app = typer.Typer(
    name="reposcribe",
    help="Scribes a repository's non-ignored files into a single context file, respecting .gitignore.",
    add_completion=False,
)


@app.command()
def main(
    project_dir: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="Path to the project root directory to scribe.",
    ),
    output_file: Optional[Path] = typer.Argument(
        None,  # <-- Default value is None
        file_okay=True,
        dir_okay=False,
        writable=True,  # Still checks parent if specified
        resolve_path=True,  # Resolve if specified
        help="Path to the output file. [default: ./output/{project_name}_context.txt]",
    ),
    # --- End Modification ---
    encoding: str = typer.Option(
        "utf-8", "--encoding", "-e", help="Encoding for reading files."
    ),
    errors: str = typer.Option(
        "ignore", "--errors", help="How to handle file read encoding errors."
    ),
    include_tree: bool = typer.Option(
        True, "--tree/--no-tree", help="Include/exclude a file tree."
    ),
    yes: bool = typer.Option(False, "--yes", "-y",
                             help="Skip confirmation prompt."),
):
    """
    Gathers non-ignored files from PROJECT_DIRECTORY, respecting .gitignore,
    and concatenates them into OUTPUT_FILE.
    """

    # --- 1. Setup & Path Resolution (with Default Handling) ---
    project_root_str = str(project_dir)  # Already resolved by Typer

    output_dir_name = "output"  # Name for the default output subdirectory
    output_file_path_str: str  # Declare variable type

    if output_file is None:
        # --- Default Output File Logic ---
        # Create default output directory relative to current working directory
        default_output_dir = Path.cwd() / output_dir_name
        try:
            default_output_dir.mkdir(parents=True, exist_ok=True)
            typer.echo(
                f"Ensured output directory exists: {default_output_dir}", err=True
            )
        except OSError as e:
            typer.secho(
                f"Error: Could not create output directory '{default_output_dir}': {e}",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)

        # Construct default filename using the project directory's name
        default_filename = f"{project_dir.name}_context.txt"
        # Combine directory and filename, then resolve to absolute path
        output_file_path = default_output_dir / default_filename
        output_file_path_str = str(output_file_path.resolve())
        typer.echo(
            f"Using default output file: {output_file_path_str}", err=True)
        # --- End Default Logic ---
    else:
        # User specified an output file, Typer already resolved it
        output_file_path_str = str(output_file)

    # --- 2. Read Ignore Rules & Create PathSpec ---
    gitignore_path = os.path.join(project_root_str, ".gitignore")
    reposcribe_ignore_path = os.path.join(
        project_root_str, ".reposcribe_ignore")

    typer.echo("Reading ignore rules...", err=True)
    ignore_file_paths = [gitignore_path, reposcribe_ignore_path]
    ignore_patterns = read_ignore_patterns(ignore_file_paths)

    # Dynamically ignore the output file (whether specified or defaulted)
    output_rel_path = None
    try:
        # Check if the FINAL output path is inside the project root
        if os.path.commonpath([project_root_str]) == os.path.commonpath(
            [project_root_str, output_file_path_str]
        ):
            if project_root_str != output_file_path_str:  # Ensure not same path
                output_rel_path = os.path.relpath(
                    output_file_path_str, project_root_str
                )
                output_rel_path = output_rel_path.replace(os.sep, "/")
                ignore_patterns.append(output_rel_path)
                typer.echo(
                    f"Dynamically ignoring output file: {output_rel_path}", err=True
                )
    except ValueError:
        pass  # Different drives (Windows), output is not inside project

    try:
        spec = pathspec.PathSpec.from_lines(
            pathspec.patterns.GitWildMatchPattern, ignore_patterns
        )
    except Exception as e:
        typer.secho(
            f"Error parsing ignore patterns: {e}", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(code=1)

    # --- 3. Find Files ---
    typer.echo(f"Scanning project directory: {project_root_str}", err=True)
    try:
        files_to_export = find_exportable_files(project_root_str, spec)
    except Exception as e:
        typer.secho(
            f"Error scanning directory: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # --- 4. Handle No Files Found ---
    if not files_to_export:
        typer.secho(
            "No files found to scribe (after applying ignore rules). Nothing to do.",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(code=0)

    # --- 5. Confirmation Step ---
    typer.echo("\nThe following files will be scribed:")
    for file_path in files_to_export:
        typer.echo(f"  - {file_path}")
    typer.echo(f"\nTotal files: {len(files_to_export)}")

    if not yes:
        try:
            # Pass the final determined output path to the confirmation message
            confirmed = typer.confirm(
                f"Proceed with scribing to '{output_file_path_str}'?"
            )
            if not confirmed:
                typer.echo("Scribing cancelled by user.")
                raise typer.Exit(code=0)
        except typer.Abort:
            typer.echo("\nScribing cancelled by user (Abort).")
            raise typer.Exit(code=130)

    # --- 6. Write Output File ---
    typer.echo(f"\nScribing files to {output_file_path_str}...", err=True)
    try:
        file_count, total_size = write_export_file(
            output_file_path_str,  # Use the final path string
            project_root_str,
            files_to_export,
            encoding,
            errors,
            include_tree,
        )
        # --- 7. Success Message ---
        typer.secho(
            f"\nSuccessfully scribed content of {file_count} files.",
            fg=typer.colors.GREEN,
        )
        typer.echo(f"Total approximate size: {total_size / 1024:.2f} KB")
        typer.echo(f"Output written to: {output_file_path_str}")

    except Exception as e:
        typer.secho(
            f"\nScribing failed during file writing.", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(code=1)


# --- Poetry Script Entry Point ---
def run():
    app()


if __name__ == "__main__":
    run()
