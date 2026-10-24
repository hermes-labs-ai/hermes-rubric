"""Experiment accounting and transport controls; no provider calls in tests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def runner():
    path = Path(__file__).parents[1] / "evals/wedge-variance/runner.py"
    spec = importlib.util.spec_from_file_location("wedge_variance_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_targets_load_without_temp_inputs(runner):
    targets = runner.load_targets()
    assert [target["id"] for target in targets] == ["T1", "T2", "T4"]
    assert len({target["sha256"] for target in targets}) == 3
    assert all((runner.REPO / target["path"]).is_file() for target in targets)
    assert all(target["intent"] and target["target_type"] for target in targets)


def test_auth_requires_positive_subscription_facts_not_exit_alone(runner, monkeypatch):
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: SimpleNamespace(
        returncode=0, stdout='{"loggedIn":false,"authMethod":"none","apiProvider":"firstParty"}'))
    assert runner.subscription_status()[0] is False
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: SimpleNamespace(
        returncode=0, stdout='{"loggedIn":true,"authMethod":"apiKey","apiProvider":"firstParty"}'))
    assert runner.subscription_status()[0] is False


def test_subscription_environment_never_uses_provider_keys(runner, monkeypatch):
    for name in runner.CREDENTIAL_ENV:
        monkeypatch.setenv(name, "synthetic-value")
    env = runner.subscription_env()
    assert not set(runner.CREDENTIAL_ENV).intersection(env)


def row(target="T1", arm="hermes-rubric", score=5, model="actual-model", status="ok"):
    return {"target_id": target, "arm": arm, "score": score,
            "actual_model": model, "status": status, "attempted": True,
            "latency_seconds": 2.0, "target_sha256": "fixed", "backend": "claude-cli"}


def test_failures_denominators_and_true_variance_ratio(runner):
    rows = [row(score=4), row(score=6), row(arm="raw-llm", score=2),
            row(arm="raw-llm", score=6), row(score=None, status="error")]
    summary = runner.summarize(rows, [{"id": "T1", "sha256": "fixed"}])
    target = summary["targets"][0]
    assert target["variance_ratio"] == 0.25
    assert target["arms"]["hermes-rubric"]["successful"] == 2
    assert target["arms"]["hermes-rubric"]["planned"] == 3
    assert target["arms"]["hermes-rubric"]["excluded"] == 1
    assert target["arms"]["hermes-rubric"]["latency_seconds"] == 6.0
    assert summary["mean_per_target_variance_ratio"] == 0.25


@pytest.mark.parametrize("models", [("one", "two"), (None, None), ("", "")])
def test_mismatched_or_missing_actual_models_cannot_be_compared(runner, models):
    rows = [row(score=4, model=models[0]), row(score=6, model=models[0]),
            row(arm="raw-llm", score=2, model=models[1]), row(arm="raw-llm", score=6, model=models[1])]
    summary = runner.summarize(rows, [{"id": "T1", "sha256": "fixed"}])
    assert summary["targets"][0]["variance_ratio"] is None
    assert summary["comparable_targets"] == 0


def test_zero_raw_variance_has_no_ratio(runner):
    rows = [row(score=4), row(score=6), row(arm="raw-llm", score=5), row(arm="raw-llm", score=5)]
    assert runner.summarize(rows, [{"id": "T1", "sha256": "fixed"}])["comparable_targets"] == 0


def test_unavailable_auth_records_every_unattempted_slot_and_preserves_outputs(runner, tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "subscription_status", lambda: (False, "expired subscription"))
    monkeypatch.setattr(runner.NativeClaude, "call", lambda *a: pytest.fail("blocked preflight called provider"))
    output = tmp_path / "run"
    assert runner.main(["--out", str(output), "--repetitions", "2"]) == 2
    rows = [json.loads(line) for line in (output / "raw-data.jsonl").read_text().splitlines()]
    assert len(rows) == 12
    assert all(row["status"] == "not_run" and row["attempted"] is False for row in rows)
    assert all(row["error"] == "expired subscription" for row in rows)
    assert "0 successful / 12 planned" in (output / "RESULTS.md").read_text()
    before = (output / "raw-data.jsonl").read_bytes()
    with pytest.raises(SystemExit) as failure:
        runner.main(["--out", str(output)])
    assert failure.value.code == 2
    assert (output / "raw-data.jsonl").read_bytes() == before


def test_failed_attempt_is_retained_without_retry(runner, tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "subscription_status", lambda: (True, "authenticated"))
    calls = []

    def failed(target, arm, rep, backend, output):
        calls.append((target["id"], arm, rep))
        return {**row(target=target["id"], arm=arm, score=None, status="error"), "error": "timeout"}

    monkeypatch.setattr(runner, "attempt", failed)
    output = tmp_path / "run"
    assert runner.main(["--out", str(output), "--repetitions", "2"]) == 2
    assert len(calls) == 1
    rows = [json.loads(line) for line in (output / "raw-data.jsonl").read_text().splitlines()]
    assert rows[0]["error"] == "timeout"
    assert len(rows) == 12
    assert all(row["status"] == "not_run" for row in rows[1:])


def test_native_transport_records_actual_identity_and_rejects_unknown(runner, tmp_path, monkeypatch):
    (tmp_path / "calls").mkdir()
    backend = runner.NativeClaude(tmp_path, 5)
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: SimpleNamespace(
        returncode=0, stdout=json.dumps({"modelUsage": {"observed-native-model": {}}, "result": "text"}), stderr=""))
    backend.begin()
    assert backend.call("frozen target", 2048) == "text"
    assert backend.models == {"observed-native-model"}
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: SimpleNamespace(
        returncode=0, stdout=json.dumps({"result": "text"}), stderr=""))
    with pytest.raises(ValueError, match="actual model"):
        backend.call("same target", 2048)
    assert len(list((tmp_path / "calls").glob("*.json"))) == 2


def test_both_arms_use_full_identical_frozen_target_and_configured_backend(runner, tmp_path, monkeypatch):
    target = runner.load_targets()[2]  # Longer than the historical 8KB default.
    (tmp_path / "calls").mkdir()
    backend = runner.NativeClaude(tmp_path, 5)
    captured = {}

    def assess(text, **kwargs):
        captured.update(text=text, **kwargs)
        backend.models.add("observed-model")
        return SimpleNamespace(aggregate=5, to_json=lambda: '{"aggregate":5}')

    def raw(prompt, max_tokens):
        captured["raw_prompt"] = prompt
        backend.models.add("observed-model")
        return '{"score":5,"rationale":"fixture"}'

    monkeypatch.setattr(runner, "assess", assess)
    monkeypatch.setattr(backend, "call", raw)
    assert runner.attempt(target, "hermes-rubric", 1, backend, tmp_path)["status"] == "ok"
    assert runner.attempt(target, "raw-llm", 1, backend, tmp_path)["status"] == "ok"
    assert captured["text"] == captured["context"] == target["text"]
    assert target["text"] in captured["raw_prompt"]
    assert captured["target_window_bytes"] > len(target["text"].encode())


def test_changed_target_or_backend_invalidates_comparison(runner):
    rows = [row(score=4), row(score=6), row(arm="raw-llm", score=2), row(arm="raw-llm", score=6)]
    rows[-1]["target_sha256"] = "changed"
    assert runner.summarize(rows, [{"id": "T1", "sha256": "fixed"}])["comparable_targets"] == 0
    rows[-1]["target_sha256"] = "fixed"
    rows[-1]["backend"] = "other"
    assert runner.summarize(rows, [{"id": "T1", "sha256": "fixed"}])["comparable_targets"] == 0
