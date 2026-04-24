"""Tests for v0.2.0 features: rubric hash + citation source-class tagging."""

import json
from unittest.mock import patch


def _rubric(dims=3):
    return {
        "rubric_intent": "test",
        "target_type": "x",
        "dimensions": [
            {"id": f"dim_{i}", "name": f"D{i}", "description": "d", "evidence_instructions": "e", "weight": 1, "hedge": False}
            for i in range(1, dims + 1)
        ],
    }


# ----- rubric hash -----

def test_rubric_hash_stable_across_key_order():
    from hermes_rubric.receipt import rubric_hash
    r1 = {"dimensions": [{"id": "a", "name": "A", "weight": 2}], "rubric_intent": "x"}
    r2 = {"rubric_intent": "x", "dimensions": [{"weight": 2, "name": "A", "id": "a"}]}
    assert rubric_hash(r1) == rubric_hash(r2)


def test_rubric_hash_changes_when_rubric_changes():
    from hermes_rubric.receipt import rubric_hash
    r1 = _rubric(3)
    r2 = _rubric(3)
    r2["dimensions"][0]["description"] = "different"
    assert rubric_hash(r1) != rubric_hash(r2)


def test_receipt_includes_rubric_hash():
    from hermes_rubric.receipt import build_receipt
    r = _rubric(2)
    receipt = build_receipt(
        intent="i", context_path="c", target_path="t", backend="claude-cli",
        rubric=r, evidence_list=[], scores=[],
        target_content="abc", context_content="def",
    )
    assert "stage_1_rubric_hash_sha256" in receipt["pipeline"]
    assert len(receipt["pipeline"]["stage_1_rubric_hash_sha256"]) == 64  # sha256 hex


# ----- source-class classifier -----

def test_classify_source_code():
    from hermes_rubric.evidence import classify_source
    assert classify_source("src/hermes_rubric/score.py:42") == "code"
    assert classify_source("lib/foo.rb:10") == "code"


def test_classify_source_test():
    from hermes_rubric.evidence import classify_source
    assert classify_source("tests/test_score.py:12") == "test"
    assert classify_source("src/foo_test.py:1") == "test"


def test_classify_source_readme():
    from hermes_rubric.evidence import classify_source
    assert classify_source("README.md") == "readme"
    assert classify_source("CHANGELOG.md") == "readme"
    assert classify_source("CONTRIBUTING.md") == "readme"


def test_classify_source_doc():
    from hermes_rubric.evidence import classify_source
    assert classify_source("docs/guide.rst") == "doc"
    assert classify_source("AGENTS.md") == "doc"
    assert classify_source("INTENT.md") == "doc"


def test_classify_source_config():
    from hermes_rubric.evidence import classify_source
    assert classify_source("pyproject.toml") == "config"
    assert classify_source(".github/workflows/ci.yml") == "config"


def test_classify_source_fallback():
    from hermes_rubric.evidence import classify_source
    assert classify_source("") == "other"
    assert classify_source("some-random-string") == "other"


# ----- score cap when all citations are self-marketing -----

def _score_resp(score, hedge=False):
    return json.dumps({"score": score, "score_rationale": "r", "evidence_drove_score": "e", "hedge_applied": hedge})


def test_readme_only_citations_cap_score_at_6():
    """If every citation is README/doc, score is capped at 6 — README prose can't outrank tests."""
    from hermes_rubric import score as score_mod
    rubric = _rubric(1)
    evidence = [{
        "dim_id": "dim_1", "dim_name": "D1",
        "evidence_found": True, "confidence": "high", "hedge": False,
        "citations": [
            {"quote": "we enforce X", "location": "README.md", "source_class": "readme"},
            {"quote": "we guarantee Y", "location": "README.md", "source_class": "readme"},
        ],
        "evidence_summary": "README claims.",
    }]
    with patch.object(score_mod.backends, "call", side_effect=[_score_resp(9)]):
        scores = score_mod.score_dimensions(rubric=rubric, evidence_list=evidence, backend="claude-cli")
    assert scores[0]["score"] == 6
    assert "README/doc" in scores[0]["score_rationale"]


def test_code_citations_not_capped():
    """Code/test citations are ground-truth — no cap applied."""
    from hermes_rubric import score as score_mod
    rubric = _rubric(1)
    evidence = [{
        "dim_id": "dim_1", "dim_name": "D1",
        "evidence_found": True, "confidence": "high", "hedge": False,
        "citations": [
            {"quote": "def foo(): return 1", "location": "src/foo.py:3", "source_class": "code"},
            {"quote": "assert foo() == 1", "location": "tests/test_foo.py:5", "source_class": "test"},
        ],
        "evidence_summary": "Code + test.",
    }]
    with patch.object(score_mod.backends, "call", side_effect=[_score_resp(9)]):
        scores = score_mod.score_dimensions(rubric=rubric, evidence_list=evidence, backend="claude-cli")
    assert scores[0]["score"] == 9
    assert scores[0]["citation_source_weight"] == 1.0


def test_mixed_citations_not_capped():
    """If even one citation is ground-truth, the README cap doesn't apply."""
    from hermes_rubric import score as score_mod
    rubric = _rubric(1)
    evidence = [{
        "dim_id": "dim_1", "dim_name": "D1",
        "evidence_found": True, "confidence": "high", "hedge": False,
        "citations": [
            {"quote": "we enforce X", "location": "README.md", "source_class": "readme"},
            {"quote": "assert hedge_applied", "location": "tests/test_adversarial.py:14", "source_class": "test"},
        ],
        "evidence_summary": "README + test.",
    }]
    with patch.object(score_mod.backends, "call", side_effect=[_score_resp(9)]):
        scores = score_mod.score_dimensions(rubric=rubric, evidence_list=evidence, backend="claude-cli")
    assert scores[0]["score"] == 9
