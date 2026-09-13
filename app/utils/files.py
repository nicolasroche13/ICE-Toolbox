from __future__ import annotations

import re
from pathlib import Path


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("._") or "ring"


def non_overwriting_path(path: Path) -> Path:
    if not path.exists():
        return path

    counter = 1
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1

