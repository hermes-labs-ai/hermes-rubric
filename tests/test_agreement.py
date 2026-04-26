"""Tests for G1: Cohen's kappa cross-backend agreement."""

import io
import json

import pytest

from hermes_rubric.agreement import (
    _bin_score,
    _pairwise_kappa,
    cohens_kappa,
    kappa_from_paths,
    main as kappa_main,
)


def _run(scores_by_name: dict[str, float]) -> dict:
    """Build a minimal hermes-rubric run-output dict from {name: score}."""
    return {
        "per_dim_scores": [
            {"dim_id": f"dim_{i}", "dim_name": name, "score": score}
            for i, (name, score) in enumerate(scores_by_name.items(), start=1)
        ]
    }


# ----- bin helpers -----

def test_bin_score_clamps_and_rounds():
    assert _bin_score(7) == 7
    assert _bin_score(7.4) == 7
    assert _bin_score(7.6) == 8
    assert _bin_score(-2) == 0
    assert _bin_score(15) == 10


def test_pairwise_kappa_identical_is_one():
    assert _pairwise_kappa([1, 5, 7, 9], [1, 5, 7, 9]) == 1.0


def test_pairwise_kappa_systematic_disagreement_is_negative():
    # Six dims, raters consistently flip between two categories.
    a = [3, 8, 3, 8, 3, 8]
    b = [8, 3, 8, 3, 8, 3]
    k = _pairwise_kappa(a, b)
    assert k < 0


# ----- end-to-end kappa -----

def test_identical_runs_kappa_is_one():
    """G1 acceptance: identical runs -> kappa = 1.0."""
    scores = {"Evidence Grounding": 8, "Claim Precision": 6, "Limitation Disclosure": 7}
    r1 = _run(scores)
    r2 = _run(scores)
    out = cohens_kappa(r1, r2)
    assert out["mean_kappa"] == 1.0
    assert out["matched_dims"] == 3
    assert out["unmatched_run1"] == []
    assert out["unmatched_run2"] == []


def test_fully_disagreeing_runs_kappa_negative():
    """G1 acceptance: fully disagreeing runs -> kappa < 0."""
    r1 = _run({"A": 2, "B": 9, "C": 2, "D": 9, "E": 2, "F": 9})
    r2 = _run({"A": 9, "B": 2, "C": 9, "D": 2, "E": 9, "F": 2})
    out = cohens_kappa(r1, r2)
    assert out["mean_kappa"] < 0
    assert out["matched_dims"] == 6


def test_partially_agreeing_runs_kappa_in_open_unit_interval():
    """G1 acceptance: realistic partial agreement -> kappa in (0, 1)."""
    # 6 dims; 4 match, 2 differ by a few categories. Expect noticeably > 0
    # but well below 1.0.
    r1 = _run({"A": 8, "B": 7, "C": 6, "D": 5, "E": 4, "F": 9})
    r2 = _run({"A": 8, "B": 7, "C": 6, "D": 5, "E": 7, "F": 3})
    out = cohens_kappa(r1, r2)
    assert 0.0 < out["mean_kappa"] < 1.0
    assert out["matched_dims"] == 6


# ----- mismatched rubric handling -----

def test_mismatched_dims_warn_and_drop():
    r1 = _run({"A": 5, "B": 6, "Shared": 7})
    r2 = _run({"X": 5, "Y": 6, "Shared": 7})
    buf = io.StringIO()
    out = cohens_kappa(r1, r2, warn_stream=buf)
    assert out["matched_dims"] == 1
    assert out["unmatched_run1"] == ["A", "B"]
    assert out["unmatched_run2"] == ["X", "Y"]
    assert "WARNING" in buf.getvalue()
    assert "rubric dimensions differ" in buf.getvalue()


def test_no_overlap_raises():
    r1 = _run({"A": 5})
    r2 = _run({"B": 5})
    with pytest.raises(ValueError, match="No matching dimensions"):
        cohens_kappa(r1, r2, warn_stream=io.StringIO())


# ----- file + CLI wrapper -----

def test_kappa_from_paths_roundtrip(tmp_path):
    scores = {"A": 7, "B": 8, "C": 5}
    p1 = tmp_path / "r1.json"
    p2 = tmp_path / "r2.json"
    p1.write_text(json.dumps(_run(scores)))
    p2.write_text(json.dumps(_run(scores)))
    out = kappa_from_paths(str(p1), str(p2))
    assert out["mean_kappa"] == 1.0


def test_kappa_cli_writes_report(tmp_path, capsys):
    scores = {"A": 7, "B": 8, "C": 5}
    p1 = tmp_path / "r1.json"
    p2 = tmp_path / "r2.json"
    out_path = tmp_path / "kappa.json"
    p1.write_text(json.dumps(_run(scores)))
    p2.write_text(json.dumps(_run(scores)))

    rc = kappa_main(["--run1", str(p1), "--run2", str(p2), "--out", str(out_path)])
    assert rc == 0
    report = json.loads(out_path.read_text())
    assert report["mean_kappa"] == 1.0
    assert report["matched_dims"] == 3


def test_kappa_cli_missing_file_returns_nonzero(tmp_path):
    rc = kappa_main(["--run1", str(tmp_path / "nope.json"), "--run2", str(tmp_path / "nope.json")])
    assert rc == 1
