#!/usr/bin/env python3
"""
Wedge-variance experiment (Gap 1 from EVAL-COVERAGE.md).

Compares variance of:
  - hermes-rubric `aggregate` score (claude-cli backend, claude-haiku-4-5)
  - raw LLM 0-10 rating (claude-cli direct, same model)
on the SAME target × SAME backend.

Target: Paper 1 ("Asymmetric Burden of Proof") section of
applied/papers-20260423.md, extracted to /tmp/var-test/T1-paper1.md (~3.2KB).

n=10 reps per arm. Outputs raw-data.jsonl + RESULTS.md.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/Users/rbr_lpci/Documents/projects/hermes-rubric")
OUT_DIR = REPO / "evals" / "wedge-variance"
TMP = Path("/tmp/var-test")
TMP.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_PATH = TMP / "T1-paper1.md"
CONTEXT_PATH = REPO / "applied" / "papers-20260423.md"
RAW_JSONL = OUT_DIR / "raw-data.jsonl"
PARTIAL = Path("/tmp/var-test-partial.jsonl")

MODEL_ID = "claude-haiku-4-5"
N = 10
INTENT = "Score this paper for publication readiness."

assert TARGET_PATH.exists(), f"Missing target: {TARGET_PATH}"
assert CONTEXT_PATH.exists(), f"Missing context: {CONTEXT_PATH}"

TARGET_TEXT = TARGET_PATH.read_text()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append_row(row: dict) -> None:
    line = json.dumps(row)
    with RAW_JSONL.open("a") as f:
        f.write(line + "\n")
    with PARTIAL.open("a") as f:
        f.write(line + "\n")


def run_hermes_rubric(rep: int) -> float | None:
    out_json = TMP / f"hr-rep{rep}.json"
    cmd = [
        "hermes-rubric",
        "--intent", INTENT,
        "--context", str(CONTEXT_PATH),
        "--target", str(TARGET_PATH),
        "--target-type", "research-paper",
        "--backend", "claude-cli",
        "--out", str(out_json),
    ]
    env = os.environ.copy()
    env.setdefault("HERMES_RUBRIC_CLAUDE_MODEL", MODEL_ID)
    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        print(f"[hr rep{rep}] TIMEOUT", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(f"[hr rep{rep}] rc={proc.returncode}: {proc.stderr[-300:]}", file=sys.stderr)
        return None
    try:
        data = json.loads(out_json.read_text())
    except Exception as e:
        print(f"[hr rep{rep}] parse fail: {e}", file=sys.stderr)
        return None
    agg = data.get("aggregate")
    if isinstance(agg, dict):
        agg = agg.get("score") or agg.get("value") or agg.get("aggregate")
    return float(agg) if agg is not None else None


PROMPT_RAW = (
    "Rate this research paper for publication readiness, 0-10. "
    "Reply with a single integer 0-10 and one sentence rationale.\n\n"
    "<paper>\n" + TARGET_TEXT + "\n</paper>"
)


def run_raw_llm(rep: int) -> tuple[float | None, str]:
    cmd = [
        "claude", "--print",
        "--exclude-dynamic-system-prompt-sections",
        "--model", MODEL_ID,
        PROMPT_RAW,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        print(f"[raw rep{rep}] TIMEOUT", file=sys.stderr)
        return None, ""
    if proc.returncode != 0:
        print(f"[raw rep{rep}] rc={proc.returncode}: {proc.stderr[-300:]}", file=sys.stderr)
        return None, proc.stdout
    text = proc.stdout.strip()
    # Find first integer 0-10 in output
    m = re.search(r"\b(10|[0-9])\b", text)
    if not m:
        return None, text
    return float(m.group(1)), text


def main() -> int:
    # Reset jsonls
    if RAW_JSONL.exists():
        RAW_JSONL.unlink()
    if PARTIAL.exists():
        PARTIAL.unlink()

    rate_limited = False

    print(f"=== Hermes-rubric arm (n={N}) ===", file=sys.stderr)
    for rep in range(1, N + 1):
        t0 = time.time()
        score = run_hermes_rubric(rep)
        dt = time.time() - t0
        print(f"  hr rep{rep}: score={score} ({dt:.1f}s)", file=sys.stderr)
        append_row({
            "arm": "hermes-rubric",
            "rep_n": rep,
            "score": score,
            "model_id": MODEL_ID,
            "timestamp_utc": utc_now(),
        })
        if score is None:
            # one retry sleep on suspected rate-limit, then accept
            if not rate_limited:
                rate_limited = True
                print("  rate-limit retry: sleeping 60s", file=sys.stderr)
                time.sleep(60)

    print(f"=== Raw LLM arm (n={N}) ===", file=sys.stderr)
    for rep in range(1, N + 1):
        t0 = time.time()
        score, text = run_raw_llm(rep)
        dt = time.time() - t0
        print(f"  raw rep{rep}: score={score} ({dt:.1f}s) [{text[:80]!r}]", file=sys.stderr)
        append_row({
            "arm": "raw-llm",
            "rep_n": rep,
            "score": score,
            "model_id": MODEL_ID,
            "timestamp_utc": utc_now(),
            "raw_text": text[:500],
        })
        if score is None:
            if not rate_limited:
                rate_limited = True
                print("  rate-limit retry: sleeping 60s", file=sys.stderr)
                time.sleep(60)

    # Summarize
    rows = [json.loads(line) for line in RAW_JSONL.read_text().splitlines() if line.strip()]
    hr = [r["score"] for r in rows if r["arm"] == "hermes-rubric" and r["score"] is not None]
    raw = [r["score"] for r in rows if r["arm"] == "raw-llm" and r["score"] is not None]

    def stats(xs):
        if not xs:
            return {"n": 0, "mean": None, "sigma": None, "min": None, "max": None}
        return {
            "n": len(xs),
            "mean": statistics.mean(xs),
            "sigma": statistics.pstdev(xs) if len(xs) > 1 else 0.0,
            "min": min(xs),
            "max": max(xs),
        }

    s_hr = stats(hr)
    s_raw = stats(raw)
    ratio = (s_hr["sigma"] / s_raw["sigma"]) if (s_raw["sigma"] and s_hr["sigma"] is not None) else None

    if ratio is None:
        verdict = "INCONCLUSIVE (insufficient data or zero raw σ)"
    elif ratio < 0.7:
        verdict = "SUPPORTED (hermes_σ < raw_σ × 0.7)"
    elif ratio <= 1.3:
        verdict = "EQUIVOCAL (0.7 ≤ hermes_σ/raw_σ ≤ 1.3)"
    else:
        verdict = f"REFUTED-AT-N={N} (hermes_σ > raw_σ × 1.3)"

    md = []
    md.append("# Wedge-Variance Empirical Comparison\n")
    md.append(f"**Date:** {utc_now()}  ")
    md.append("**Target:** Paper 1 (\"Asymmetric Burden of Proof\") from `applied/papers-20260423.md` (~3.2KB)  ")
    md.append(f"**Backend:** claude-cli, model `{MODEL_ID}`  ")
    md.append(f"**Reps:** {N} per arm  ")
    md.append(f"**Intent:** \"{INTENT}\"\n")
    md.append("## Results\n")
    md.append("| Arm | n | mean | σ (pstdev) | min | max |")
    md.append("|---|---|---|---|---|---|")
    for name, s in [("hermes-rubric", s_hr), ("raw-llm", s_raw)]:
        if s["n"]:
            md.append(f"| {name} | {s['n']} | {s['mean']:.3f} | {s['sigma']:.3f} | {s['min']:.2f} | {s['max']:.2f} |")
        else:
            md.append(f"| {name} | 0 | — | — | — | — |")
    md.append("")
    md.append(f"**Variance ratio:** hermes_σ / raw_σ = {('%.3f' % ratio) if ratio is not None else 'n/a'}\n")
    md.append(f"**Verdict:** {verdict}\n")
    md.append("## Interpretation\n")
    if ratio is None:
        md.append("Insufficient successful runs (or zero variance in the raw arm) to compute a meaningful ratio. Re-run with more reps before drawing any wedge conclusion.\n")
    elif ratio < 0.7:
        md.append(
            "At n=10 per arm on a single target, hermes-rubric exhibits substantially lower run-to-run variance "
            "than direct rating with the same model. The wedge claim — that the rubric's evidence-first decomposition "
            "stabilizes scoring — is supported at this n. Confirmation at larger n and across multiple targets is "
            "still required before treating this as a reliability guarantee.\n"
        )
    elif ratio <= 1.3:
        md.append(
            "At n=10 per arm on a single target, hermes-rubric's variance is comparable to a raw 0-10 rating from the "
            "same model (within the 0.7–1.3 envelope). The variance-reduction wedge claim is **not supported** by this "
            "experiment. FLAGSHIP-SPEC's wedge language should drop or qualify the variance-reduction claim until a "
            "larger-N, multi-target study is run.\n"
        )
    else:
        md.append(
            "At n=10 per arm on a single target, hermes-rubric is **more** variable than a direct 0-10 rating from the "
            "same model. The wedge claim is refuted at this n. This needs investigation — likely sources include "
            "prompt-length stochasticity in multi-stage scoring, dimension-weight sensitivity, or evidence-collection "
            "noise — before any reliability claim can be made publicly.\n"
        )

    (OUT_DIR / "RESULTS.md").write_text("\n".join(md))

    # Print machine-readable summary block
    print("\n=== SUMMARY ===")
    print(f"HERMES-RUBRIC ARM:  n={s_hr['n']}, mean={s_hr['mean']}, σ={s_hr['sigma']}, min={s_hr['min']}, max={s_hr['max']}")
    print(f"RAW-LLM ARM:        n={s_raw['n']}, mean={s_raw['mean']}, σ={s_raw['sigma']}, min={s_raw['min']}, max={s_raw['max']}")
    print(f"VARIANCE RATIO:     {ratio}")
    print(f"VERDICT:            {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
