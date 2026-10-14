"""Product version from the repository VERSION file."""

from __future__ import annotations

from pathlib import Path


def product_version() -> str:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "VERSION"
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8").strip()
            if text:
                return text
    raise RuntimeError("VERSION file was not found next to the application.")
