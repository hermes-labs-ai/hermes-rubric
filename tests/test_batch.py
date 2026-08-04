"""Tests for --batch mode: dim_id-keyed reassembly, fallback paths, clamp preservation."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_rubric():
    return json.loads((FIXTURE_DIR / "frozen_rubric.json").read_text())


def _ev(dim_id, *, found=True, confidence="high", hedge=False, citations=None):
    return {
        "dim_id": dim_id,
        "dim_name": dim_id,
        "evidence_found": found,
        "confidence": confidence,
        "hedge": hedge,
        "citations": citations if citations is not None else [
            {"quote": "fixture quote", "location": "src/foo.py:10", "source_class": "code"}
        ],
        "evidence_summary": f"summary for {dim_id}",
    }


def _score_obj(dim_id, score, **extra):
    base = {
        "dim_id": dim_id,
        "dim_name": dim_id,
        "score": score,
        "score_rationale": "based on evidence",
        "evidence_drove_score": "fixture quote",
        "hedge_applied": False,
    }
    base.update(extra)
    return base


def test_batched_score_dim_id_keyed_reassembly():
    """LLM returns dims out of order; result aligns with rubric dim order via dim_id."""
    from hermes_rubric import score as score_mod

    rubric = _load_rubric()
    evidence_list = [_ev(d["id"]) for d in rubric["dimensions"]]
    # Return in reverse order
    out_of_order = [
        _score_obj("fr_d", 5, hedge_applied=True),
        _score_obj("fr_c", 7),
        _score_obj("fr_b", 6),
        _score_obj("fr_a", 9),
    ]
    raw = json.dumps(out_of_order)

    with patch.object(score_mod.backends, "call", return_value=raw):
        scores = score_mod.score_dimensions(
            rubric=rubric, evidence_list=evidence_list, backend="stub", batch=True
        )

    # Output order must follow evidence_list (which follows rubric)
    assert [s["dim_id"] for s in scores] == ["fr_a", "fr_b", "fr_c", "fr_d"]
    assert [s["score"] for s in scores] == [9, 6, 7, 5]


def test_batched_score_missing_dim_falls_back():
    """LLM returns 3 of 4 dims; the missing dim gets score=3, hedge_applied=true."""
    from hermes_rubric import score as score_mod

    rubric = _load_rubric()
    evidence_list = [_ev(d["id"]) for d in rubric["dimensions"]]
    raw = json.dumps([
        _score_obj("fr_a", 8),
        _score_obj("fr_b", 6),
        _score_obj("fr_d", 5, hedge_applied=True),
        # fr_c missing
    ])

    with patch.object(score_mod.backends, "call", return_value=raw):
        scores = score_mod.score_dimensions(
            rubric=rubric, evidence_list=evidence_list, backend="stub", batch=True
        )

    by_id = {s["dim_id"]: s for s in scores}
    assert by_id["fr_c"]["score"] == 3
    assert by_id["fr_c"]["hedge_applied"] is True
    assert by_id["fr_a"]["score"] == 8


def test_batched_scores_pin_canonical_dimension_identity():
    """Batched Stage 3 may omit or drift names; rubric identity still wins."""
    from hermes_rubric import score as score_mod

    rubric = _load_rubric()
    evidence_list = [_ev(d["id"]) for d in rubric["dimensions"]]
    raw = json.dumps([
        _score_obj("fr_a", 8, dim_name="Drifted name"),
        {key: value for key, value in _score_obj("fr_b", 6).items() if key != "dim_name"},
        _score_obj("fr_c", 7, dim_name="Also drifted"),
        _score_obj("fr_d", 5, dim_name="Wrong"),
    ])

    with patch.object(score_mod.backends, "call", return_value=raw):
        scores = score_mod.score_dimensions(
            rubric=rubric,
            evidence_list=evidence_list,
            backend="stub",
            batch=True,
        )

    assert [(s["dim_id"], s["dim_name"]) for s in scores] == [
        (dim["id"], dim["name"]) for dim in rubric["dimensions"]
    ]
    assert [s["score"] for s in scores] == [8, 6, 7, 5]


def test_batched_parse_failure_falls_back_to_per_dim():
    """Malformed JSON on batched call → per-dim fallback fires."""
    from hermes_rubric import score as score_mod

    rubric = _load_rubric()
    evidence_list = [_ev(d["id"]) for d in rubric["dimensions"]]
    # First call (batched) returns junk; subsequent calls (per-dim) return valid singletons
    responses = ["totally not json"] + [
        json.dumps(_score_obj(d["id"], 7)) for d in rubric["dimensions"]
    ]

    with patch.object(score_mod.backends, "call", side_effect=responses):
        scores = score_mod.score_dimensions(
            rubric=rubric, evidence_list=evidence_list, backend="stub", batch=True
        )

    assert len(scores) == 4
    assert all(s["score"] == 7 for s in scores)


def test_batched_preserves_clamp_suffixes():
    """Hedge, no-evidence, and self-marketing clamps still apply byte-for-byte in batched mode."""
    from hermes_rubric import score as score_mod

    rubric = _load_rubric()
    evidence_list = [
        _ev("fr_a", confidence="low", hedge=True),       # → hedge clamp
        _ev("fr_b", found=False),                          # → no-evidence cap
        _ev("fr_c", citations=[
            {"quote": "from readme", "location": "README.md", "source_class": "readme"}
        ]),                                                 # → self-marketing cap
        _ev("fr_d"),                                        # → no clamp
    ]
    raw = json.dumps([
        _score_obj("fr_a", 10),  # batched LLM gives 10 → hedge clamps to 7
        _score_obj("fr_b", 9),   # → no-evidence caps at 3
        _score_obj("fr_c", 9),   # → self-marketing caps at 6
        _score_obj("fr_d", 8),
    ])

    with patch.object(score_mod.backends, "call", return_value=raw):
        scores = score_mod.score_dimensions(
            rubric=rubric, evidence_list=evidence_list, backend="stub", batch=True
        )

    by_id = {s["dim_id"]: s for s in scores}
    assert by_id["fr_a"]["score"] == 7
    assert "[Score clamped to [3,7] due to low-confidence evidence.]" in by_id["fr_a"]["score_rationale"]
    assert by_id["fr_b"]["score"] == 3
    assert "[Score capped at 3: no evidence found.]" in by_id["fr_b"]["score_rationale"]
    assert by_id["fr_c"]["score"] == 6
    assert "[Score capped at 6: all citations are README/doc (self-marketing); no code/test evidence.]" in by_id["fr_c"]["score_rationale"]
    assert by_id["fr_d"]["score"] == 8


def test_batched_vs_per_dim_golden_equivalence():
    """Same fixture + deterministic stub returning identical canned scores → identical dim_summaries."""
    from hermes_rubric import score as score_mod

    rubric = _load_rubric()
    evidence_list = [_ev(d["id"]) for d in rubric["dimensions"]]
    canned = {d["id"]: 7 for d in rubric["dimensions"]}

    def per_dim_stub(prompt, backend=None):
        # Per-dim prompt mentions exactly one dim_id; find it
        for dim_id in canned:
            if f'"{dim_id}"' in prompt or f'DIMENSION: {dim_id}' in prompt or dim_id in prompt:
                return json.dumps(_score_obj(dim_id, canned[dim_id]))
        return json.dumps(_score_obj(list(canned)[0], 3))

    def batched_stub(prompt, backend=None):
        return json.dumps([_score_obj(dim_id, canned[dim_id]) for dim_id in canned])

    with patch.object(score_mod.backends, "call", side_effect=per_dim_stub):
        per_dim_scores = score_mod.score_dimensions(
            rubric=rubric, evidence_list=evidence_list, backend="stub", batch=False
        )
    with patch.object(score_mod.backends, "call", side_effect=batched_stub):
        batched_scores = score_mod.score_dimensions(
            rubric=rubric, evidence_list=evidence_list, backend="stub", batch=True
        )

    pd_agg = score_mod.compute_aggregate(rubric=rubric, scores=per_dim_scores)
    b_agg = score_mod.compute_aggregate(rubric=rubric, scores=batched_scores)

    assert [d["dim_id"] for d in pd_agg["dim_summaries"]] == [d["dim_id"] for d in b_agg["dim_summaries"]]
    assert [d["score"] for d in pd_agg["dim_summaries"]] == [d["score"] for d in b_agg["dim_summaries"]]
    assert pd_agg["aggregate"] == b_agg["aggregate"]


def test_batched_evidence_dim_id_keyed_reassembly():
    """Batched evidence: LLM returns dims out of order; output aligns with rubric order."""
    from hermes_rubric import evidence as ev_mod

    rubric = _load_rubric()
    target_text = "the target body, irrelevant to dim_id keying"
    out_of_order = [
        {"dim_id": "fr_d", "evidence_found": True, "confidence": "medium", "hedge": False,
         "citations": [{"quote": "q4", "location": "src/x.py:1", "source_class": "code"}],
         "evidence_summary": "s4"},
        {"dim_id": "fr_a", "evidence_found": True, "confidence": "high", "hedge": False,
         "citations": [{"quote": "q1", "location": "tests/test_x.py:1", "source_class": "test"}],
         "evidence_summary": "s1"},
        {"dim_id": "fr_b", "evidence_found": True, "confidence": "high", "hedge": False,
         "citations": [{"quote": "q2", "location": "src/x.py:5", "source_class": "code"}],
         "evidence_summary": "s2"},
        {"dim_id": "fr_c", "evidence_found": True, "confidence": "high", "hedge": False,
         "citations": [{"quote": "q3", "location": "src/x.py:9", "source_class": "code"}],
         "evidence_summary": "s3"},
    ]

    with patch.object(ev_mod.backends, "call", return_value=json.dumps(out_of_order)):
        result = ev_mod.collect_evidence(
            rubric=rubric, target_content=target_text, target_path="t.md",
            backend="stub", batch=True,
        )

    assert [e["dim_id"] for e in result] == ["fr_a", "fr_b", "fr_c", "fr_d"]
    assert [e["evidence_summary"] for e in result] == ["s1", "s2", "s3", "s4"]


def test_extract_json_array_rejects_non_array():
    """A bare object (not array) raises BatchParseError."""
    from hermes_rubric import evidence as ev_mod

    with pytest.raises(ev_mod.BatchParseError):
        ev_mod._extract_json_array('{"dim_id": "fr_a"}', {"fr_a"})


def test_extract_json_array_zero_matches_raises():
    """Array with zero matching dim_ids raises (triggers fallback)."""
    from hermes_rubric import evidence as ev_mod

    with pytest.raises(ev_mod.BatchParseError):
        ev_mod._extract_json_array('[{"dim_id": "unrelated"}]', {"fr_a", "fr_b"})
