#!/usr/bin/env python3
"""Require a CSV header to exactly match a csv-quality-gate profile's columns.

The pinned csv-quality-gate action checks only that required columns are
present. This check closes the gap: the header row must equal the profile's
``required_columns`` list exactly, in order, with no extra, missing, or
whitespace-padded names. It checks CSV structure only, not experiment
conclusions.

Usage:
    python3 scripts/check_manifest_header.py CSV_PATH CONFIG_TOML PROFILE
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path


def header_errors(header: list[str] | None, expected: list[str]) -> list[str]:
    """Return human-readable reasons ``header`` differs from ``expected``."""
    if header is None:
        return ["CSV is empty: no header row found"]
    if header == expected:
        return []

    errors: list[str] = []
    missing = [name for name in expected if name not in header]
    extra = [name for name in header if name not in expected]
    if missing:
        errors.append(f"missing columns: {missing}")
    if extra:
        errors.append(f"unexpected extra columns: {extra}")
    duplicates = sorted({name for name in header if header.count(name) > 1})
    if duplicates:
        errors.append(f"duplicate columns: {duplicates}")
    if not errors:
        errors.append("column order differs from the expected order")
    errors.append(f"expected header: {expected}")
    errors.append(f"actual header:   {header}")
    return errors


def read_header(csv_path: Path) -> list[str] | None:
    with csv_path.open(newline="", encoding="utf-8") as f:
        return next(csv.reader(f), None)


def load_expected_columns(config_path: Path, profile: str) -> list[str]:
    import tomllib  # Python >= 3.11; only needed when reading the config.

    with config_path.open("rb") as f:
        config = tomllib.load(f)
    columns = config["profiles"][profile]["required_columns"]
    if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns):
        raise ValueError(f"profile {profile!r} required_columns must be a list of strings")
    return columns


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    csv_path, config_path, profile = Path(argv[0]), Path(argv[1]), argv[2]
    expected = load_expected_columns(config_path, profile)
    errors = header_errors(read_header(csv_path), expected)
    if errors:
        print(f"FAIL: {csv_path} header does not exactly match profile {profile!r}")
        for line in errors:
            print(f"  {line}")
        return 1
    print(f"PASS: {csv_path} header exactly matches profile {profile!r} ({len(expected)} columns)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
