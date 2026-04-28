"""Tests for class-aware rubric templates (v0.2)."""
import pytest

from hermes_rubric import classes as classes_mod


def test_list_classes_returns_bundled_set():
    available = classes_mod.list_classes()
    assert "social-post" in available
    assert "show-hn-post" in available
    assert "linkedin-post" in available
    assert "outreach-email" in available
    assert "repo-readme" in available
    assert len(available) == 5


def test_load_repo_readme_class_has_seven_axes():
    """repo-readme class encodes 7 fixed FAANG-Series-A axes (added 2026-04-28)."""
    data = classes_mod.load_class("repo-readme")
    assert data["artifact_class"] == "repo-readme"
    assert "dimensions" in data
    assert len(data["dimensions"]) == 7
    expected_dim_ids = {
        "conversion_shape", "scrutiny_readiness", "evidence_grounding",
        "anti_academic", "voice_consistency", "doc_surface_separation",
        "link_integrity",
    }
    actual_dim_ids = {d["id"] for d in data["dimensions"]}
    assert actual_dim_ids == expected_dim_ids
    total_weight = sum(d["weight"] for d in data["dimensions"])
    assert total_weight == 16


def test_load_unknown_class_raises():
    with pytest.raises(ValueError, match="Unknown artifact class"):
        classes_mod.load_class("nonexistent-class")


def test_load_social_post_class_has_required_fields():
    data = classes_mod.load_class("social-post")
    assert data["artifact_class"] == "social-post"
    assert "dimensions" in data
    assert len(data["dimensions"]) >= 5
    for dim in data["dimensions"]:
        assert "id" in dim
        assert "name" in dim
        assert "description" in dim
        assert "evidence_instructions" in dim
        assert "weight" in dim


def test_load_outreach_email_has_banned_subjects():
    data = classes_mod.load_class("outreach-email")
    assert "banned_subject_patterns" in data
    assert "AI Act" in data["banned_subject_patterns"]
    assert "deadline" in data["banned_subject_patterns"]


def test_to_rubric_shape_matches_synthesize_output():
    """The class-template rubric must match the shape synthesize() produces,
    so downstream evidence + score code is unchanged."""
    data = classes_mod.load_class("show-hn-post")
    rubric = classes_mod.to_rubric(data)
    assert "rubric_intent" in rubric
    assert "target_type" in rubric
    assert "dimensions" in rubric
    assert rubric["target_type"] == "show-hn-post"
    assert rubric["rubric_source"] == "class-template"
    for dim in rubric["dimensions"]:
        assert "id" in dim
        assert "name" in dim
        assert "weight" in dim


def test_class_load_is_cached():
    """Repeated loads of the same class must hit the cache (deterministic)."""
    a = classes_mod.load_class("social-post")
    b = classes_mod.load_class("social-post")
    assert a is b


def test_all_four_classes_have_llm_fool_dim():
    """Every social-content class must have an llm_fool dim — that's the slop floor."""
    for class_name in ["social-post", "show-hn-post", "linkedin-post", "outreach-email"]:
        data = classes_mod.load_class(class_name)
        dim_ids = [d["id"] for d in data["dimensions"]]
        assert "llm_fool" in dim_ids, f"{class_name} missing llm_fool dim"


def test_all_four_classes_have_fab_block_dim():
    """Every class must have fab_block — verifiability is non-optional."""
    for class_name in ["social-post", "show-hn-post", "linkedin-post", "outreach-email"]:
        data = classes_mod.load_class(class_name)
        dim_ids = [d["id"] for d in data["dimensions"]]
        assert "fab_block" in dim_ids, f"{class_name} missing fab_block dim"


def test_class_yamls_are_deterministic():
    """Loading the same class twice produces identical rubrics — the v0.2 invariant."""
    rubric_a = classes_mod.to_rubric(classes_mod.load_class("social-post"))
    classes_mod.load_class.cache_clear()
    rubric_b = classes_mod.to_rubric(classes_mod.load_class("social-post"))
    assert rubric_a == rubric_b
