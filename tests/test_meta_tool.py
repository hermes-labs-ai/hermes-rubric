"""Tests for meta_tool.hermes_meta_rubric.

Mirrors patterns from tests/test_score.py. No backend calls in any test —
the run_meta_rubric integration uses dependency injection at the
synthesize/collect/score boundary.
"""

import copy
import json
from pathlib import Path

import pytest

from meta_tool.hermes_meta_rubric import (
    PolicyError,
    apply_policy_clamps,
    apply_weight_strategy,
    load_registry,
    select_policy,
    validate_policy,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _good_policy(policy_id="test-v1", **overrides):
    base = {
        "policy_id": policy_id,
        "policy_version": "1.0.0",
        "target_type_match": ["test-target"],
        "source_class_caps": {
            "code": None, "test": None, "config": None,
            "doc": None, "readme": None, "other": None,
        },
        "window_bytes": 16000,
        "dim_weight_strategy": "preserve",
        "prompt_template_id": "default",
        "no_evidence_floor": 3,
        "hedge_band": {"lo": 3, "hi": 7},
        "rationale": "test",
        "fallback_policy_id": "default-v1",
    }
    base.update(overrides)
    return base


def _evidence(dim_id, *, source_class="readme", evidence_found=True, hedge=False):
    return {
        "dim_id": dim_id,
        "evidence_found": evidence_found,
        "confidence": "low" if hedge else "high",
        "hedge": hedge,
        "citations": [
            {"quote": "x", "location": "section foo", "source_class": source_class},
            {"quote": "y", "location": "section bar", "source_class": source_class},
        ],
        "evidence_summary": "summary",
    }


def _score(dim_id, score, *, rationale=""):
    return {
        "dim_id": dim_id,
        "dim_name": dim_id,
        "score": score,
        "score_rationale": rationale,
        "evidence_drove_score": "ev",
        "hedge_applied": False,
    }


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def test_validate_policy_accepts_minimal_good_policy():
    validate_policy(_good_policy())


def test_validate_policy_rejects_missing_required_field():
    pol = _good_policy()
    del pol["window_bytes"]
    with pytest.raises(PolicyError, match="missing required fields"):
        validate_policy(pol)


def test_validate_policy_rejects_window_out_of_range():
    with pytest.raises(PolicyError, match="window_bytes"):
        validate_policy(_good_policy(window_bytes=500))
    with pytest.raises(PolicyError, match="window_bytes"):
        validate_policy(_good_policy(window_bytes=999_999))


def test_validate_policy_rejects_unknown_source_class_in_caps():
    pol = _good_policy()
    pol["source_class_caps"]["bogus_class"] = 5
    with pytest.raises(PolicyError, match="unknown source_class"):
        validate_policy(pol)


def test_validate_policy_rejects_invalid_strategy():
    with pytest.raises(PolicyError, match="dim_weight_strategy"):
        validate_policy(_good_policy(dim_weight_strategy="learn"))


def test_validate_policy_rejects_invalid_hedge_band():
    with pytest.raises(PolicyError, match="hedge_band"):
        validate_policy(_good_policy(hedge_band={"lo": 7, "hi": 3}))


# ---------------------------------------------------------------------------
# Registry + dispatch
# ---------------------------------------------------------------------------

def test_load_registry_default_returns_three_baseline_policies():
    registry = load_registry()
    ids = {p["policy_id"] for p in registry}
    assert {"preprint-paper-v1", "repo-v1", "default-v1"} <= ids


def test_select_policy_first_match_wins_on_target_type():
    registry = load_registry()
    pol = select_policy("preprint-paper", registry)
    assert pol["policy_id"] == "preprint-paper-v1"
    pol2 = select_policy("paper", registry)
    assert pol2["policy_id"] == "preprint-paper-v1"


def test_select_policy_falls_through_to_wildcard():
    registry = load_registry()
    pol = select_policy("totally-unknown-type", registry)
    # default-v1 carries '*' in its target_type_match
    assert pol["policy_id"] == "default-v1"


def test_select_policy_repo_matches_repo_policy():
    registry = load_registry()
    pol = select_policy("repo", registry)
    assert pol["policy_id"] == "repo-v1"
    assert pol["source_class_caps"]["readme"] == 6  # cap preserved


def test_load_registry_rejects_invalid_file(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([{"policy_id": "x"}]))  # missing fields
    with pytest.raises(PolicyError):
        load_registry(bad)


# ---------------------------------------------------------------------------
# Re-clamp behavior (the heart of the value-add)
# ---------------------------------------------------------------------------

def test_apply_policy_clamps_lifts_cap_when_policy_says_null():
    """The original tool capped a README-only-cited dim at 6; with the
    preprint-paper policy (caps=null) we recover +2."""
    pol = _good_policy()  # all caps null
    ev = [_evidence("dim_1", source_class="readme")]
    scores = [_score("dim_1", 6, rationale="[Score capped at 6: all citations are README/doc (self-marketing); no code/test evidence.]")]
    out = apply_policy_clamps(scores, ev, pol)
    assert out[0]["score"] == 8  # 6 + 2 recovery
    assert "cap lifted by policy" in out[0]["score_rationale"]


def test_apply_policy_clamps_preserves_cap_when_policy_says_six():
    """The repo-v1 policy keeps the cap; uncap-eligible signal must NOT fire."""
    pol = _good_policy()
    pol["source_class_caps"]["readme"] = 6
    ev = [_evidence("dim_1", source_class="readme")]
    scores = [_score("dim_1", 6, rationale="[Score capped at 6: ...]")]
    out = apply_policy_clamps(scores, ev, pol)
    assert out[0]["score"] == 6  # untouched


def test_apply_policy_clamps_re_clamps_hedge_band():
    pol = _good_policy(hedge_band={"lo": 4, "hi": 6})
    ev = [_evidence("dim_1", hedge=True)]
    scores = [_score("dim_1", 9)]
    out = apply_policy_clamps(scores, ev, pol)
    assert out[0]["score"] == 6  # clamped to upper bound


def test_apply_policy_clamps_no_evidence_floor():
    pol = _good_policy(no_evidence_floor=2)
    ev = [_evidence("dim_1", evidence_found=False)]
    scores = [_score("dim_1", 7)]
    out = apply_policy_clamps(scores, ev, pol)
    assert out[0]["score"] == 2


def test_apply_policy_clamps_records_meta_metadata():
    pol = _good_policy(policy_id="my-v1")
    ev = [_evidence("dim_1", source_class="code")]
    scores = [_score("dim_1", 7)]
    out = apply_policy_clamps(scores, ev, pol)
    assert out[0]["meta_policy_id"] == "my-v1"
    assert out[0]["meta_dominant_source_class"] == "code"


def test_apply_policy_clamps_caps_when_policy_sets_explicit_cap():
    pol = _good_policy()
    pol["source_class_caps"]["doc"] = 5
    ev = [_evidence("dim_1", source_class="doc")]
    scores = [_score("dim_1", 9)]
    out = apply_policy_clamps(scores, ev, pol)
    assert out[0]["score"] == 5


# ---------------------------------------------------------------------------
# Weight strategy
# ---------------------------------------------------------------------------

def test_apply_weight_strategy_flatten_sets_all_weights_to_1():
    pol = _good_policy(dim_weight_strategy="flatten")
    rubric = {
        "rubric_intent": "x", "target_type": "y",
        "dimensions": [
            {"id": "dim_1", "name": "A", "description": "", "evidence_instructions": "", "weight": 3, "hedge": False},
            {"id": "dim_2", "name": "B", "description": "", "evidence_instructions": "", "weight": 2, "hedge": False},
        ],
    }
    out = apply_weight_strategy(rubric, pol)
    assert all(d["weight"] == 1 for d in out["dimensions"])


def test_apply_weight_strategy_preserve_is_identity():
    pol = _good_policy(dim_weight_strategy="preserve")
    rubric = {
        "rubric_intent": "x", "target_type": "y",
        "dimensions": [{"id": "dim_1", "name": "A", "description": "", "evidence_instructions": "", "weight": 3, "hedge": False}],
    }
    out = apply_weight_strategy(rubric, pol)
    assert out["dimensions"][0]["weight"] == 3


def test_apply_weight_strategy_amplify_load_bearing():
    pol = _good_policy(dim_weight_strategy="amplify-load-bearing")
    rubric = {
        "rubric_intent": "x", "target_type": "y",
        "dimensions": [
            {"id": "dim_1", "name": "A", "description": "", "evidence_instructions": "", "weight": 1, "hedge": False, "load_bearing": True},
            {"id": "dim_2", "name": "B", "description": "", "evidence_instructions": "", "weight": 1, "hedge": False},
        ],
    }
    out = apply_weight_strategy(rubric, pol)
    assert out["dimensions"][0]["weight"] == 2
    assert out["dimensions"][1]["weight"] == 1


# ---------------------------------------------------------------------------
# End-to-end sanity: preprint policy lifts >= one cap on a paper-shaped target
# ---------------------------------------------------------------------------

def test_run_meta_rubric_with_rubric_file_skips_synthesize(tmp_path, monkeypatch):
    """V1 (Mission C): --rubric-file flag must skip synthesize() and load
    rubric from disk verbatim. The rest of the pipeline runs as normal."""
    from meta_tool import hermes_meta_rubric as hmr

    # Provided rubric on disk
    rubric_in = {
        "rubric_intent": "test intent",
        "target_type": "preprint-paper",
        "dimensions": [
            {
                "id": "dim_1", "name": "A", "description": "desc A",
                "evidence_instructions": "look A", "weight": 2, "hedge": False,
            },
            {
                "id": "dim_2", "name": "B", "description": "desc B",
                "evidence_instructions": "look B", "weight": 1, "hedge": False,
            },
            {
                "id": "dim_3", "name": "C", "description": "desc C",
                "evidence_instructions": "look C", "weight": 1, "hedge": False,
            },
        ],
    }
    rubric_path = tmp_path / "rubric.json"
    rubric_path.write_text(json.dumps(rubric_in))

    target_path = tmp_path / "target.md"
    target_path.write_text("# target\nbody content here.\n")
    context_path = tmp_path / "context.md"
    context_path.write_text("context summary\n")

    # Sentinel that fails loudly if synthesize is called
    def _fail_synthesize(*a, **kw):
        raise AssertionError("synthesize() must NOT be called when rubric_file is provided")

    def _fake_collect(rubric, target_content, target_path, backend, batch=False):
        return [
            {
                "dim_id": d["id"],
                "evidence_found": True,
                "confidence": "high",
                "hedge": False,
                "citations": [{"quote": "x", "location": "section foo", "source_class": "doc"}],
                "evidence_summary": "ok",
                "dim_name": d["name"],
                "source_class_mix": {"doc": 1, "code": 0, "test": 0, "config": 0, "readme": 0, "other": 0},
            }
            for d in rubric["dimensions"]
        ]

    def _fake_score(rubric, evidence_list, backend, batch=False):
        return [
            {
                "dim_id": ev["dim_id"], "dim_name": ev["dim_name"],
                "score": 7, "score_rationale": "ok",
                "evidence_drove_score": "x", "hedge_applied": False,
            }
            for ev in evidence_list
        ]

    def _fake_build_receipt(**kw):
        return {"backend": kw.get("backend", ""), "rubric": kw.get("rubric")}

    def _fake_detect():
        return "fake-backend"

    monkeypatch.setattr(hmr, "synthesize", _fail_synthesize)
    monkeypatch.setattr(hmr, "collect_evidence", _fake_collect)
    monkeypatch.setattr(hmr, "score_dimensions", _fake_score)
    monkeypatch.setattr(hmr, "build_receipt", _fake_build_receipt)
    monkeypatch.setattr(hmr._backends, "detect", _fake_detect)

    result = hmr.run_meta_rubric(
        intent="audit",
        context_path=str(context_path),
        target_path=str(target_path),
        target_type="preprint-paper",
        rubric_file=str(rubric_path),
    )

    # Rubric carried through verbatim (intent + dim ids preserved)
    assert result["rubric"]["rubric_intent"] == "test intent"
    assert [d["id"] for d in result["rubric"]["dimensions"]] == ["dim_1", "dim_2", "dim_3"]
    # Receipt notes file-source for auditability
    assert result["meta_policy"]["rubric_source"].startswith("file:")
    assert str(rubric_path) in result["meta_policy"]["rubric_source"]
    # Pipeline ran end-to-end (per_dim_scores populated)
    assert len(result["per_dim_scores"]) == 3


def test_load_rubric_file_rejects_invalid_shape(tmp_path):
    from meta_tool.hermes_meta_rubric import load_rubric_file

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"rubric_intent": "x"}))  # no dimensions
    with pytest.raises(ValueError):
        load_rubric_file(bad)


def test_load_rubric_file_missing_file(tmp_path):
    from meta_tool.hermes_meta_rubric import load_rubric_file

    with pytest.raises(FileNotFoundError):
        load_rubric_file(tmp_path / "does-not-exist.json")


def test_preprint_policy_lifts_caps_for_paper_target():
    registry = load_registry()
    pol = select_policy("preprint-paper", registry)
    # With this policy, ALL caps must be null (lifted)
    assert all(v is None for v in pol["source_class_caps"].values())
    # And window must be substantially larger than original 8000
    assert pol["window_bytes"] >= 30_000
