"""Exact-header check for the committed batch-run manifest CSV."""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_manifest_header.py"
CONFIG = ROOT / ".github" / "csv-quality-gate-manifest.toml"
MANIFEST = ROOT / "experiments" / "batch-equiv-2026-04-25" / "RUNS-MANIFEST.csv"
PROFILE = "batch_runs_manifest"

EXPECTED = [
    "target_id", "mode", "sub_exp", "rep", "aggregate",
    "fallback_used", "n_backend_calls", "latency_seconds",
    "tool_version", "backend_label", "started_at", "path",
]

if not SCRIPT.is_file():
    pytest.skip("manifest header script not present", allow_module_level=True)

_spec = importlib.util.spec_from_file_location("check_manifest_header", SCRIPT)
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def _write(tmp_path, header):
    path = tmp_path / "manifest.csv"
    row = ",".join(["x"] * len(header))
    path.write_text(",".join(header) + "\n" + row + "\n", encoding="utf-8")
    return path


def test_exact_header_passes(tmp_path):
    header = check.read_header(_write(tmp_path, EXPECTED))
    assert check.header_errors(header, EXPECTED) == []


def test_reordered_header_fails(tmp_path):
    reordered = EXPECTED[:]
    reordered[0], reordered[1] = reordered[1], reordered[0]
    errors = check.header_errors(check.read_header(_write(tmp_path, reordered)), EXPECTED)
    assert "column order differs from the expected order" in errors


def test_extra_column_fails(tmp_path):
    errors = check.header_errors(
        check.read_header(_write(tmp_path, EXPECTED + ["notes"])), EXPECTED
    )
    assert any("unexpected extra columns: ['notes']" in e for e in errors)


def test_missing_column_fails(tmp_path):
    errors = check.header_errors(check.read_header(_write(tmp_path, EXPECTED[:-1])), EXPECTED)
    assert any("missing columns: ['path']" in e for e in errors)


def test_padded_column_fails(tmp_path):
    padded = EXPECTED[:]
    padded[2] = " sub_exp"
    errors = check.header_errors(check.read_header(_write(tmp_path, padded)), EXPECTED)
    assert errors


def test_empty_csv_fails(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")
    assert check.header_errors(check.read_header(path), EXPECTED)


@pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib requires Python 3.11+")
def test_main_on_committed_manifest_and_drift(tmp_path, capsys):
    if not (CONFIG.is_file() and MANIFEST.is_file()):
        pytest.skip("committed manifest/config not present")
    assert check.load_expected_columns(CONFIG, PROFILE) == EXPECTED
    assert check.main([str(MANIFEST), str(CONFIG), PROFILE]) == 0
    drifted = _write(tmp_path, [EXPECTED[1], EXPECTED[0], *EXPECTED[2:], "extra"])
    assert check.main([str(drifted), str(CONFIG), PROFILE]) == 1
    assert "does not exactly match" in capsys.readouterr().out
