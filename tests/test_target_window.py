"""Tests for --target-window-bytes truncation warning (G8)."""

from pathlib import Path


def test_warning_fires_on_oversize_input(tmp_path, capsys):
    """When target file > window_bytes, a stderr warning is emitted."""
    from hermes_rubric.evidence import read_target

    big = tmp_path / "big.md"
    big.write_text("x" * 9000)

    content, resolved = read_target(str(big), window_bytes=8000)
    captured = capsys.readouterr()

    assert "WARNING" in captured.err
    assert "9000 > 8000" in captured.err
    assert "rubric-passthrough-pattern" in captured.err
    # Single-file mode returns full text — the *prompt* layer enforces the cap.
    assert len(content) == 9000


def test_no_warning_on_undersize_input(tmp_path, capsys):
    """Files at or under the window do not warn."""
    from hermes_rubric.evidence import read_target

    small = tmp_path / "small.md"
    small.write_text("x" * 500)

    content, _ = read_target(str(small), window_bytes=8000)
    captured = capsys.readouterr()

    assert "WARNING" not in captured.err
    assert len(content) == 500


def test_custom_window_bytes_threshold(tmp_path, capsys):
    """A smaller window triggers the warning at a smaller threshold."""
    from hermes_rubric.evidence import read_target

    f = tmp_path / "mid.md"
    f.write_text("x" * 1500)

    # Under default 8000 — no warning
    read_target(str(f), window_bytes=8000)
    assert "WARNING" not in capsys.readouterr().err

    # Tight window — warning fires
    read_target(str(f), window_bytes=1000)
    err = capsys.readouterr().err
    assert "WARNING" in err
    assert "1500 > 1000" in err


def test_context_warns_on_oversize(tmp_path, capsys):
    """read_context warns when single-file context exceeds the window."""
    from hermes_rubric.evidence import read_context

    ctx = tmp_path / "ctx.md"
    ctx.write_text("c" * 12000)

    out = read_context(str(ctx), window_bytes=8000)
    err = capsys.readouterr().err

    assert "WARNING" in err
    assert len(out) == 8000
