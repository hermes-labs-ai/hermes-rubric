"""Truthful Stage-1 visibility reporting."""

from __future__ import annotations

from hermes_rubric.inputs import load_target_path, load_text


def test_memory_coverage_is_complete_within_window():
    coverage = load_text("hello", name="answer.md").coverage(8000)
    assert coverage.status == "complete"
    assert coverage.visible_bytes == coverage.total_bytes == 5
    assert coverage.total_sources == coverage.considered_sources == 1


def test_memory_coverage_uses_utf8_safe_byte_facts():
    coverage = load_text("ééé", name="answer.md").coverage(5)
    assert coverage.status == "partial"
    assert coverage.visible_bytes == 4
    assert coverage.total_bytes == 6
    assert "first 5 UTF-8 bytes" in coverage.limitations[0]


def test_directory_discloses_global_and_source_limits(tmp_path):
    for index in range(52):
        (tmp_path / f"{index:02}.md").write_text("x" * 20)
    loaded = load_target_path(tmp_path, window_bytes=10)
    coverage = loaded.coverage(10)
    assert coverage.status == "partial"
    assert coverage.total_sources == 52
    assert coverage.considered_sources == 50
    assert coverage.visible_bytes is None
    limitations = " ".join(coverage.limitations)
    assert "first 50 of 52" in limitations
    assert "50 loaded source(s)" in limitations
    assert "loaded target representation" in limitations


def test_path_loader_retains_legacy_truncation_warning(tmp_path, capsys):
    target = tmp_path / "large.md"
    target.write_text("x" * 20)
    loaded = load_target_path(target, window_bytes=10)
    assert loaded.total_bytes == 20
    assert "WARNING: target file exceeds --target-window-bytes" in capsys.readouterr().err
