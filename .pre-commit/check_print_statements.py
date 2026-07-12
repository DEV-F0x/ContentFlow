"""
Pre-commit hook: block commits that contain Python print() calls.

print() left in application code is almost always leftover debug output
that bypasses the app's configured logging (app/core/logging.py) — it
won't be tagged with a level/logger name and, in production, won't show
up in the JSON logs shipped to Grafana / Loki. Use `logging` instead.

A call can be deliberately kept with a trailing ``print-ignore`` comment
on the same line (e.g. a CLI script that's meant to print to stdout).

Usage (as a pre-commit hook, or standalone):
    python .pre-commit/check_print_statements.py <file> [<file> ...]
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

EXCLUDED_PATH_PARTS = (
    "/.pre-commit/",
    "/node_modules/",
    "/.git/",
)


def is_excluded(path: str) -> bool:
    normalized = "/" + path.replace("\\", "/")
    return any(part in normalized for part in EXCLUDED_PATH_PARTS)


def _line_ignored(line: str) -> bool:
    return "print-ignore" in line


def check_file(path: str) -> list[str]:
    if is_excluded(path) or not path.endswith(".py"):
        return []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(text, filename=path)
    except SyntaxError:
        return []

    lines = text.splitlines()
    errors = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "print"
        ):
            continue
        line = lines[node.lineno - 1] if node.lineno - 1 < len(lines) else ""
        if _line_ignored(line):
            continue
        errors.append(
            f"{path}:{node.lineno}: print() call — remove it or replace "
            f"it with `logging` (see app/core/logging.py)."
        )
    return errors


def main(argv: list[str]) -> int:
    if not argv:
        return 0

    all_errors: list[str] = []
    for path in argv:
        all_errors.extend(check_file(path))

    if all_errors:
        print("Print statement check failed:\n")
        for err in all_errors:
            print(f"  {err}")
        print(
            "\nIf a print() is intentional (e.g. a CLI script), append a "
            "'print-ignore' comment to that line to allow it through."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
