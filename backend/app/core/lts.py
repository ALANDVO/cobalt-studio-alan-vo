"""Published Node.js LTS codenames used when a pin says ``lts/*`` or ``lts/<name>``.

Snapshot date: 2026-10-14, from the public Node.js release schedule.
Node 26 was still Current on that date and had no codename, so it is not an
LTS line. ``lts/*`` means the last line in this table (krypton, major 24),
not the highest installed major.
"""

from __future__ import annotations

SNAPSHOT = "2026-10-14"

LTS_LINES: tuple[tuple[str, int], ...] = (
    ("argon", 4),
    ("boron", 6),
    ("carbon", 8),
    ("dubnium", 10),
    ("erbium", 12),
    ("fermium", 14),
    ("gallium", 16),
    ("hydrogen", 18),
    ("iron", 20),
    ("jod", 22),
    ("krypton", 24),
)


def latest() -> tuple[str, int]:
    return LTS_LINES[-1]


def major_for(name: str) -> int | None:
    key = name.strip().lower()
    for codename, major in LTS_LINES:
        if codename == key:
            return major
    return None
