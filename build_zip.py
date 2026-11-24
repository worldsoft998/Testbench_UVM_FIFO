#!/usr/bin/env python3
"""
build_zip.py
------------
Builds a single downloadable ZIP of the entire AId-UVO-RT repository tree.

Usage (run from the repository root):
    python build_zip.py [output.zip]

If no output path is given, the archive is written to:
    ./AId-UVO-RT_<timestamp>.zip

The following are excluded from the archive:
  - .git/ and .cline-home/ (tooling / session data)
  - __pycache__ and *.pyc
  - build artifacts (*.dll, *.log, *.vcd, transcript, vsim.prv, ...)
  - user-generated results under results/*/ (folder templates are kept)
  - *.zip archives

This script does NOT run any simulation or training code.
"""

import argparse
import datetime as _dt
import os
import sys
import zipfile

# Directories/files to exclude from the archive.
EXCLUDE_DIRS = {
    ".git",
    ".cline-home",
    "__pycache__",
    ".venv",
    "venv",
    "env",
}

EXCLUDE_FILE_SUFFIXES = (
    ".pyc",
    ".pyo",
    ".dll",
    ".so",
    ".sl",
    ".log",
    ".vcd",
    ".fsm",
    ".ucdb",
    ".wlf",
    ".wdb",
    ".shm",
    ".obj",
    ".exp",
    ".lib",
    ".zip",
)

EXCLUDE_FILE_NAMES = {
    "transcript",
    "vsim.prv",
    ".DS_Store",
    "Thumbs.db",
}

# Keep the results folder structure but drop user-generated run contents.
RESULTS_KEEP = {
    "results",
    "results/baseline",
    "results/srie",
    "results/blackbox",
}

# .gitkeep placeholders should be kept so empty result folders survive in ZIP.
GITKEEP = ".gitkeep"


def _should_exclude_dir(dirname):
    return dirname in EXCLUDE_DIRS


def _should_exclude_file(path, relpath):
    name = os.path.basename(path)
    if name in EXCLUDE_FILE_NAMES:
        return True
    if name.endswith(EXCLUDE_FILE_SUFFIXES):
        return True
    # Inside results/, keep only the folder templates and .gitkeep files.
    if relpath.startswith("results" + os.sep) or relpath == "results":
        if relpath not in RESULTS_KEEP and name != GITKEEP:
            return True
    return False


def build_zip(output_path=None, root=None):
    if root is None:
        root = os.path.dirname(os.path.abspath(__file__))

    if output_path is None:
        ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(root, f"AId-UVO-RT_{ts}.zip")

    output_path = os.path.abspath(output_path)
    output_name = os.path.basename(output_path)

    abs_files = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        # Filter directories in-place so we do not descend into excluded ones.
        dirnames[:] = [d for d in dirnames if not _should_exclude_dir(d)]

        for fname in filenames:
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root)

            # Never archive the output zip itself (avoid recursion).
            if fname == output_name:
                continue

            if _should_exclude_file(full, rel):
                continue

            abs_files.append((full, rel))

    abs_files.sort(key=lambda x: x[1])

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for full, rel in abs_files:
            zf.write(full, rel)

    return output_path, len(abs_files)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build a single downloadable ZIP of the AId-UVO-RT repository."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="Output ZIP path (default: ./AId-UVO-RT_<timestamp>.zip)",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Repository root (default: directory containing this script)",
    )
    args = parser.parse_args(argv)

    archive, count = build_zip(output_path=args.output, root=args.root)
    print(f"[build_zip] Archive written: {archive}")
    print(f"[build_zip] Files included:  {count}")
    print("[build_zip] No simulation or training code was executed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
