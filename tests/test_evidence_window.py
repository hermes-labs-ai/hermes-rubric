"""Regression coverage for Stage-2 target-window visibility."""

import json
import sys
from unittest.mock import patch

import pytest


def _dimension(dim_id: str) -> dict:
    return {
        "id": dim_id,
        "name": f"Dimension {dim_id}",
        "description": "Find the unique marker.",
        "evidence_instructions": "Report whether the unique marker is visible.",
        "weight": 1,
        "hedge": False,
    }


def _evidence(dim_id: str) -> dict:
    return {
        "dim_id": dim_id,
        "evidence_found": True,
        "confidence": "high",
        "hedge": False,
        "citations": [],
        "evidence_summary": "marker inspected",
    }


@pytest.mark.parametrize("batch", [False, True])
def test_requested_window_exposes_marker_after_character_6000(batch):
    """Both Stage-2 paths honor a requested window larger than the old 6k cap."""
    from hermes_rubric import evidence as evidence_mod

    marker = "UNIQUE_MARKER_AFTER_CHARACTER_6000"
    target_content = ("x" * 6100) + marker
    dims = [_dimension("dim_a")]
    if batch:
        dims.append(_dimension("dim_b"))
    prompts = []

    def backend_response(prompt, backend=None):
        prompts.append(prompt)
        if batch:
            return json.dumps([_evidence(dim["id"]) for dim in dims])
        return json.dumps(_evidence("dim_a"))

    with patch.object(evidence_mod.backends, "call", side_effect=backend_response):
        evidence_mod.collect_evidence(
            rubric={"dimensions": dims},
            target_content=target_content,
            target_path="paper.md",
            backend="stub",
            batch=batch,
            target_window_bytes=7000,
        )

    assert prompts
    assert all(marker in prompt for prompt in prompts)
    assert all(
        "truncated at configured target window" not in prompt for prompt in prompts
    )


@pytest.mark.parametrize("batch", [False, True])
def test_remaining_truncation_is_explicit_in_each_stage_2_prompt(batch):
    """Any tail hidden by the configured window is diagnosed inside the prompt."""
    from hermes_rubric import evidence as evidence_mod

    hidden_marker = "HIDDEN_TAIL_MARKER"
    target_content = ("x" * 6500) + hidden_marker
    dims = [_dimension("dim_a")]
    if batch:
        dims.append(_dimension("dim_b"))
    prompts = []

    def backend_response(prompt, backend=None):
        prompts.append(prompt)
        if batch:
            return json.dumps([_evidence(dim["id"]) for dim in dims])
        return json.dumps(_evidence("dim_a"))

    with patch.object(evidence_mod.backends, "call", side_effect=backend_response):
        evidence_mod.collect_evidence(
            rubric={"dimensions": dims},
            target_content=target_content,
            target_path="paper.md",
            backend="stub",
            batch=batch,
            target_window_bytes=6200,
        )

    diagnostic = (
        f"[... truncated at configured target window 6200 bytes "
        f"of {len(target_content)} total ...]"
    )
    assert prompts
    assert all(diagnostic in prompt for prompt in prompts)
    assert all(hidden_marker not in prompt for prompt in prompts)


@pytest.mark.parametrize("batch", [False, True])
def test_stage_2_window_enforces_utf8_bytes(batch):
    """The public byte window never exposes more UTF-8 content than configured."""
    from hermes_rubric import evidence as evidence_mod

    dims = [_dimension("dim_a")]
    if batch:
        dims.append(_dimension("dim_b"))
    prompts = []

    def backend_response(prompt, backend=None):
        prompts.append(prompt)
        if batch:
            return json.dumps([_evidence(dim["id"]) for dim in dims])
        return json.dumps(_evidence("dim_a"))

    with patch.object(evidence_mod.backends, "call", side_effect=backend_response):
        evidence_mod.collect_evidence(
            rubric={"dimensions": dims},
            target_content="é" * 10,
            target_path="paper.md",
            backend="stub",
            batch=batch,
            target_window_bytes=10,
        )

    assert prompts
    assert all("é" * 5 in prompt for prompt in prompts)
    assert all("é" * 6 not in prompt for prompt in prompts)
    assert all("10 bytes of 20 total" in prompt for prompt in prompts)


def test_pointer_id_rejects_quote_from_a_different_section():
    """A valid pointer cannot launder a quote from another section."""
    from hermes_rubric import evidence as evidence_mod

    target_content = (
        "## 3. Privacy note printed at end of every ingest run\nold context\n\n"
        "## 8. Implementation notes\n"
        "File count: 6,718 JSONL files in `~/.claude/projects/`.\n"
    )
    response = {
        "dim_id": "tail",
        "evidence_found": True,
        "confidence": "high",
        "hedge": False,
        "citations": [{
            "quote": "old context",
            "evidence_id": "S8:E1",
            "location": "3. Privacy note printed at end of every ingest run",
            "source_class": "doc",
        }],
        "evidence_summary": "tail marker found",
    }
    prompts = []

    def backend_response(prompt, backend=None):
        prompts.append(prompt)
        return json.dumps(response)

    with patch.object(evidence_mod.backends, "call", side_effect=backend_response):
        result = evidence_mod.collect_evidence(
            rubric={"dimensions": [_dimension("tail")]},
            target_content=target_content,
            target_path="spec.md",
            backend="stub",
            target_window_bytes=25000,
        )

    assert '<SECTION id="S8:E1" title="8. Implementation notes">' in prompts[0]
    assert result[0]["citations"] == []
    assert result[0]["evidence_found"] is False
    assert result[0]["hedge"] is True


def test_invalid_stage_2_window_fails_closed():
    from hermes_rubric import evidence as evidence_mod

    with pytest.raises(ValueError, match="positive integer"):
        evidence_mod.collect_evidence(
            rubric={"dimensions": [_dimension("dim_a")]},
            target_content="target",
            target_path="paper.md",
            backend="stub",
            target_window_bytes=0,
        )


def test_cli_forwards_configured_window_to_stage_2(tmp_path, monkeypatch):
    """The CLI flag, not an independent Stage-2 constant, controls visibility."""
    from hermes_rubric import cli

    target = tmp_path / "paper.md"
    context = tmp_path / "context.txt"
    output = tmp_path / "receipt.json"
    target.write_text("paper")
    context.write_text("context")
    captured = {}

    class FakeResult:
        def to_json(self):
            return "{}"

    def fake_assess_path(*args, **kwargs):
        captured.update(kwargs)
        return FakeResult()

    monkeypatch.setattr(cli, "assess_path", fake_assess_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hermes-rubric",
            "--intent",
            "inspect",
            "--context",
            str(context),
            "--target",
            str(target),
            "--target-type",
            "paper",
            "--target-window-bytes",
            "7000",
            "--out",
            str(output),
        ],
    )

    cli.main()

    assert captured["target_window_bytes"] == 7000
    assert output.is_file()


def test_large_target_window_does_not_expand_stage_1_context(tmp_path, monkeypatch):
    """Large evidence reviews retain the bounded synthesis context by default."""
    from hermes_rubric import cli

    target = tmp_path / "paper.md"
    context = tmp_path / "context.txt"
    output = tmp_path / "receipt.json"
    target.write_text("paper")
    context.write_text("context")
    windows = {}

    class FakeResult:
        def to_json(self):
            return "{}"

    def fake_assess_path(*args, **kwargs):
        windows["context"] = kwargs["context_window_bytes"]
        windows["target"] = kwargs["target_window_bytes"]
        return FakeResult()

    monkeypatch.setattr(cli, "assess_path", fake_assess_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hermes-rubric", "--intent", "inspect", "--context", str(context),
            "--target", str(target), "--target-type", "paper",
            "--target-window-bytes", "25000", "--out", str(output),
        ],
    )

    cli.main()

    assert windows == {"context": 8000, "target": 25000}
