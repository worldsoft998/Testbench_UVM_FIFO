"""CSV / JSON / coverage I/O helpers for the optimizer.

All file operations are local. No network access.
"""

from __future__ import annotations

import csv
import json
import os
from typing import Any, Dict, List


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def write_csv(path: str, rows: List[Dict[str, Any]], fieldnames: List[str] | None = None) -> None:
    """Write a list of dicts to CSV, appending if the file already exists."""
    ensure_dir(os.path.dirname(os.path.abspath(path)))
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    file_exists = os.path.isfile(path) and os.path.getsize(path) > 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def read_csv(path: str) -> List[Dict[str, str]]:
    if not os.path.isfile(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_json(path: str, data: Any) -> None:
    ensure_dir(os.path.dirname(os.path.abspath(path)))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def read_json(path: str) -> Any:
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


__all__ = ["ensure_dir", "write_csv", "read_csv", "write_json", "read_json"]
