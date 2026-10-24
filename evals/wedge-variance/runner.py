#!/usr/bin/env python3
"""Compare stored-target Hermes assessments and raw ratings on native Claude.

No paid-provider credentials, model overrides, retries, or historical-output resets.
Only observed matching model identities can enter a per-target comparison.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from hermes_rubric import assess, backends  # noqa: E402

# Maintainer-fixed shapes: evidence-rich code, thin product blurb, research report.
TARGET_IDS = ("T1", "T2", "T4")
FROZEN = REPO / "experiments/batch-equiv-2026-04-25/frozen/claude"
CREDENTIAL_ENV = (
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN",
    "ANTHROPIC_BASE_URL", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def subscription_env():
    env = os.environ.copy()
    for key in CREDENTIAL_ENV:
        env.pop(key, None)
    return env


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("score is not numeric")
    if not math.isfinite(value) or not 0 <= value <= 10:
        raise ValueError("score is outside finite 0-10 range")
    return float(value)


def load_targets():
    targets = []
    for target_id in TARGET_IDS:
        path = FROZEN / target_id / "target.txt"
        text = path.read_text(encoding="utf-8")
        rubric = json.loads(path.with_name("rubric.json").read_text())
        targets.append({"id": target_id, "text": text,
                        "path": str(path.relative_to(REPO)),
                        "sha256": hashlib.sha256(text.encode()).hexdigest(),
                        "intent": rubric["rubric_intent"],
                        "target_type": rubric["target_type"]})
    return targets


def subscription_status():
    """A zero exit alone is insufficient: native status can report loggedIn=false."""
    try:
        proc = subprocess.run(["claude", "auth", "status", "--json"],
                              env=subscription_env(), capture_output=True, text=True, timeout=15)
        status = json.loads(proc.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return False, f"native subscription status unavailable: {type(exc).__name__}"
    if not status.get("loggedIn"):
        return False, "native Claude subscription is not logged in (expired/unavailable)"
    if status.get("authMethod") != "claude.ai" or status.get("apiProvider") != "firstParty":
        return False, "native status does not establish the existing first-party subscription route"
    return True, "native first-party subscription authenticated"


class NativeClaude:
    """Evaluation-only JSON instrumentation of the existing native backend.

    Core scoring/backend sources are unchanged. Both arms share this transport,
    existing configured model, CLI context mode and observed model identity.
    """
    name = "wedge-native-claude"

    def __init__(self, output: Path, timeout: float):
        self.output, self.timeout = output, timeout
        self.configured_model = backends.get_backend("claude-cli").model_id()
        self.models: set[str] = set()
        self.deadline = 0.0
        self.last_text = ""

    def model_id(self):
        return self.configured_model

    def availability(self):
        return subscription_status()[0]

    def begin(self):
        self.models.clear()
        self.last_text = ""
        self.deadline = time.monotonic() + self.timeout

    def call(self, prompt: str, max_tokens: int):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("assessment attempt timeout")
        command = ["claude", "--print", "--exclude-dynamic-system-prompt-sections",
                   "--model", self.configured_model, "--output-format", "json", prompt]
        record = {"timestamp_utc": utc_now(), "configured_model": self.configured_model,
                  "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()}
        try:
            proc = subprocess.run(command, env=subscription_env(), capture_output=True,
                                  text=True, timeout=remaining)
            record.update(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
            envelope = json.loads(proc.stdout)
            if proc.returncode or envelope.get("is_error"):
                raise RuntimeError("native Claude returned a failed result; inspect call receipt")
            models = set(envelope.get("modelUsage", {}))
            if len(models) != 1 or any(not isinstance(model, str) or not model for model in models):
                raise ValueError("native envelope does not establish exactly one actual model")
            self.models.update(models)
            if len(self.models) != 1:
                raise ValueError("actual model changed within one assessment")
            self.last_text = envelope["result"]
            if not isinstance(self.last_text, str):
                raise ValueError("native result is not text")
            return self.last_text
        except subprocess.TimeoutExpired:
            record["error"] = "native call exceeded attempt timeout"
            raise
        finally:
            (self.output / "calls" / (uuid.uuid4().hex + ".json")).write_text(
                json.dumps(record, indent=2) + "\n", encoding="utf-8")


def attempt(target, arm, rep, backend, output):
    started = time.monotonic()
    row = {"target_id": target["id"], "target_sha256": target["sha256"],
           "arm": arm, "rep_n": rep, "backend": "claude-cli",
           "configured_model": backend.model_id(), "timestamp_utc": utc_now(),
           "attempted": True, "status": "error", "score": None, "actual_model": None}
    backend.begin()
    try:
        if arm == "hermes-rubric":
            # Both arms receive the exact complete target, not the historical
            # 8KB prefix in one arm and full research report in the other.
            result = assess(target["text"], intent=target["intent"], context=target["text"],
                            target_name=target["path"], target_type=target["target_type"],
                            backend=backend.name, target_window_bytes=len(target["text"].encode()) + 1,
                            context_window_bytes=len(target["text"].encode()) + 1)
            row["score"] = number(result.aggregate)
            (output / f"{target['id']}-{arm}-{rep}.json").write_text(result.to_json() + "\n")
        else:
            prompt = (f"{target['intent']}\nRate this target from 0 to 10. "
                      "Return only JSON with score (number) and rationale (string).\n\n"
                      f"<target>\n{target['text']}\n</target>")
            row["raw_text"] = backend.call(prompt, max_tokens=2048)
            row["score"] = number(json.loads(row["raw_text"])["score"])
        if len(backend.models) != 1:
            raise ValueError("actual model identity unavailable")
        row.update(status="ok", actual_model=next(iter(backend.models)))
    except Exception as exc:
        row.update(score=None, error=f"{type(exc).__name__}: {exc}",
                   observed_models=sorted(backend.models))
    row["latency_seconds"] = time.monotonic() - started
    return row


def arm_stats(rows):
    scores = [number(row["score"]) for row in rows if row["status"] == "ok"]
    return {"planned": len(rows), "attempted": sum(row["attempted"] for row in rows),
            "successful": len(scores), "excluded": len(rows) - len(scores),
            "mean": statistics.mean(scores) if scores else None,
            "sigma": statistics.pstdev(scores) if len(scores) >= 2 else None,
            "min": min(scores) if scores else None, "max": max(scores) if scores else None,
            "latency_seconds": sum(row.get("latency_seconds", 0) for row in rows)}


def summarize(rows, targets):
    result = {"targets": [], "planned": len(rows),
              "successful": sum(row["status"] == "ok" for row in rows)}
    for target in targets:
        arms = {arm: [row for row in rows if row["target_id"] == target["id"] and row["arm"] == arm]
                for arm in ("hermes-rubric", "raw-llm")}
        stats = {arm: arm_stats(items) for arm, items in arms.items()}
        identities = [{r.get("actual_model") for r in items if r["status"] == "ok"}
                      for items in arms.values()]
        same_inputs = all(row.get("target_sha256") == target["sha256"]
                          and row.get("backend") == "claude-cli" for items in arms.values()
                          for row in items if row["status"] == "ok")
        matching = (same_inputs and len(identities[0]) == 1 and identities[0] == identities[1]
                    and all(isinstance(model, str) and model for model in identities[0]))
        hr, raw = stats["hermes-rubric"], stats["raw-llm"]
        comparable = matching and hr["sigma"] is not None and raw["sigma"] not in (None, 0)
        result["targets"].append({"id": target["id"], "sha256": target["sha256"],
                                  "arms": stats, "matching_actual_model": matching,
                                  "actual_models": [sorted(m for m in s if m) for s in identities],
                                  "variance_ratio": (hr["sigma"] / raw["sigma"]) ** 2 if comparable else None})
    ratios = [target["variance_ratio"] for target in result["targets"] if target["variance_ratio"] is not None]
    result.update(comparable_targets=len(ratios), excluded=len(rows) - result["successful"],
                  mean_per_target_variance_ratio=statistics.mean(ratios) if ratios else None)
    return result


def report(summary, reason):
    lines = ["# Multi-target variance comparison", "", f"Status: {reason}", "",
             "Descriptive observations only. No general reliability, validity, or variance-reduction claim.",
             "Failures are excluded with denominators; no automatic retries or pooled cross-target scores.",
             "Native contextual CLI configuration can influence both arms.", "",
             "| Target | Arm | Successful / planned | Attempted | Excluded | Mean | Sigma | Min | Max | Latency (s) |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for target in summary["targets"]:
        for arm, stats in target["arms"].items():
            lines.append(f"| {target['id']} | {arm} | {stats['successful']} / {stats['planned']} | "
                         f"{stats['attempted']} | {stats['excluded']} | {stats['mean']} | {stats['sigma']} | "
                         f"{stats['min']} | {stats['max']} | {stats['latency_seconds']:.3f} |")
        lines.extend(["", f"{target['id']} actual models by arm: {target['actual_models']}; "
                      f"matching identity: {target['matching_actual_model']}; "
                      f"variance ratio (Hermes variance / raw variance): {target['variance_ratio']}", ""])
    lines.extend([f"Total: {summary['successful']} successful / {summary['planned']} planned; "
                  f"{summary['excluded']} excluded.",
                  f"Comparable targets: {summary['comparable_targets']}; descriptive mean per-target "
                  f"variance ratio: {summary['mean_per_target_variance_ratio']}.",
                  "A missing or zero raw variance yields no ratio. Missing/mismatched actual model identity "
                  "invalidates comparison. Configured aliases alone are not actual-model evidence."])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="New output directory; existing outputs are refused")
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=600, help="Whole-attempt deadline in seconds")
    args = parser.parse_args(argv)
    if args.repetitions < 2 or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("at least two repetitions and a finite positive timeout are required")
    targets = load_targets()
    # Exclusive creation prevents resets, accidental reuse, and retry laundering.
    try:
        args.out.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        parser.error(f"cannot create a new output directory: {exc}")
    (args.out / "calls").mkdir()
    ready, reason = subscription_status()
    backend = NativeClaude(args.out, args.timeout)
    backends.register(backend, replace=True)
    manifest = {"started_utc": utc_now(), "backend": "claude-cli",
                "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "python_version": sys.version.split()[0],
                "configured_model": backend.model_id(), "actual_model": "recorded per attempt only",
                "repetitions_per_arm": args.repetitions, "timeout_seconds": args.timeout,
                "preflight_ready": ready, "preflight_reason": reason,
                "targets": [{k: v for k, v in target.items() if k != "text"} for target in targets]}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    rows = []
    with (args.out / "raw-data.jsonl").open("x", encoding="utf-8") as stream:
        for target in targets:
            for rep in range(1, args.repetitions + 1):
                for arm in ("hermes-rubric", "raw-llm"):
                    if ready:
                        row = attempt(target, arm, rep, backend, args.out)
                    else:
                        row = {"target_id": target["id"], "target_sha256": target["sha256"],
                               "arm": arm, "rep_n": rep, "status": "not_run", "attempted": False,
                               "backend": "claude-cli", "configured_model": backend.model_id(),
                               "actual_model": None,
                               "score": None, "latency_seconds": 0, "error": reason}
                    rows.append(row)
                    stream.write(json.dumps(row) + "\n")
                    stream.flush()
                    # A failed provider/assessment run is retained and ends this
                    # bounded attempt; later slots are explicit, not silent retries.
                    if row["status"] == "error":
                        ready, reason = False, "stopped after failed attempt; inspect raw-data and call receipts"
    summary = summarize(rows, targets)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    (args.out / "RESULTS.md").write_text(report(summary, reason), encoding="utf-8")
    print(json.dumps({"output": str(args.out), "successful": summary["successful"],
                      "planned": summary["planned"], "comparable_targets": summary["comparable_targets"],
                      "preflight_ready": manifest["preflight_ready"]}))
    return 0 if summary["successful"] == summary["planned"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
