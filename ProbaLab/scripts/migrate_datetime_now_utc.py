"""Codemod : datetime.now() / datetime.utcnow() → datetime.now(timezone.utc).

Also ensures `from datetime import timezone` is present in each modified file.
Handles both top-level and inline (function-scoped) `from datetime import ...` statements.

Usage:
    python -m scripts.migrate_datetime_now_utc --dry-run
    python -m scripts.migrate_datetime_now_utc --apply
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

PATTERN_NOW = re.compile(r"\bdatetime\.now\(\s*\)")
PATTERN_UTCNOW = re.compile(r"\bdatetime\.utcnow\(\s*\)")

ROOT = Path(__file__).parent.parent


def _add_timezone_to_import(match: re.Match) -> str:
    """Add `timezone` to a `from datetime import ...` line if not already present."""
    full_line = match.group(0)
    imports_part = match.group(1)
    if "timezone" in imports_part:
        return full_line
    return f"from datetime import {imports_part.strip()}, timezone"


# Matches any `from datetime import ...` line (including indented / inline ones)
PATTERN_DT_IMPORT = re.compile(r"from datetime import ([^\n\\]+)")


def process_file(path: Path, apply: bool) -> int:
    if path.suffix != ".py":
        return 0
    if "scripts/migrate_datetime" in str(path):
        return 0
    source = path.read_text()
    new_source = PATTERN_NOW.sub("datetime.now(timezone.utc)", source)
    new_source = PATTERN_UTCNOW.sub("datetime.now(timezone.utc)", new_source)
    if new_source == source:
        return 0

    # Patch every `from datetime import ...` line to include `timezone`
    new_source = PATTERN_DT_IMPORT.sub(_add_timezone_to_import, new_source)

    count = len(PATTERN_NOW.findall(source)) + len(PATTERN_UTCNOW.findall(source))
    if apply:
        path.write_text(new_source)
    print(f"[{'APPLY' if apply else 'DRY'}] {path.relative_to(ROOT)} — {count} replacement(s)")
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    total = 0
    for py_file in ROOT.rglob("*.py"):
        if any(part in py_file.parts for part in (".venv", "node_modules", "__pycache__", "migrations")):
            continue
        total += process_file(py_file, args.apply)
    print(f"\nTotal: {total} replacements across the repo.")


if __name__ == "__main__":
    main()
