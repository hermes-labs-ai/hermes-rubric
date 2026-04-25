"""Experiment runner: batched-vs-per-dim equivalence in hermes-rubric.

Phases:
  freeze    — synthesize rubric, collect evidence per-dim, write frozen/{tid}/{rubric,evidence}.json
  pilot     — sub-exp A on T1 only, N=3 each mode, for variance estimation
  main_a    — sub-exp A on all targets, N from --n-a (default 5)
  main_b    — sub-exp B on all targets, N from --n-b (default 3)
  validate  — ollama validation, sub-exp A on all targets, N=3, temp=0 seed=42

All phases write per-run JSON to runs/{phase}/{target}_{mode}_rep{n}_{ts}.json
and append a row to RUNS-MANIFEST.csv.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_rubric import __version__
from hermes_rubric import backends as backends_mod
from hermes_rubric.evidence import (
    _BATCHED_EVIDENCE_PROMPT_TEMPLATE,
    _EVIDENCE_PROMPT_TEMPLATE,
    collect_evidence,
    read_context,
    read_target,
)
from hermes_rubric.score import (
    _BATCHED_SCORE_PROMPT_TEMPLATE,
    _SCORE_PROMPT_TEMPLATE,
    compute_aggregate,
    score_dimensions,
)
from hermes_rubric.synthesize import synthesize

EXP_ROOT = Path(__file__).parent
FROZEN_ROOT = EXP_ROOT / "frozen"
RUNS = EXP_ROOT / "runs"
MANIFEST = EXP_ROOT / "RUNS-MANIFEST.csv"

_BACKEND_SHORT = {
    "claude-cli": "claude",
    "ollama-local": "ollama",
    "dashscope-qwen": "qwen",
    "google-gemini": "gemini",
}


def frozen_dir(backend: str) -> Path:
    return FROZEN_ROOT / _BACKEND_SHORT.get(backend, backend)

# Deterministic ordering seed
SEED = 42

# 5 targets defined here; paths resolved at freeze time
TARGETS: dict[str, dict[str, str]] = {
    "T1": {
        "label": "high-evidence Python repo",
        "intent": "Score this small Python utility on engineering qualities (tests, docs, error handling).",
        "target": str(Path.home() / "Documents/projects/agent-convergence-scorer/src"),
        "context": str(Path.home() / "Documents/projects/agent-convergence-scorer/README.md"),
        "target_type": "python-tool",
        "expected_clamp": "none",
    },
    "T2": {
        "label": "thin-evidence product blurb",
        "intent": "Score this product description on engineering substance.",
        "target": str(EXP_ROOT / "fixtures/T2_blurb.md"),
        "context": str(EXP_ROOT / "fixtures/T2_blurb.md"),
        "target_type": "marketing-doc",
        "expected_clamp": "hedge",
    },
    "T3": {
        "label": "all-README repo (no code)",
        "intent": "Score this repo on engineering qualities (tests, code, error handling).",
        "target": str(EXP_ROOT / "fixtures/T3_readme_only/"),
        "context": str(EXP_ROOT / "fixtures/T3_readme_only/README.md"),
        "target_type": "repo",
        "expected_clamp": "self-marketing",
    },
    "T4": {
        "label": "research-corpus markdown report",
        "intent": "Score this research report on rigor and evidence.",
        "target": str(Path.home() / "Documents/projects/hermes-rubric/applied"),
        "context": str(Path.home() / "Documents/projects/hermes-rubric/applied"),
        "target_type": "research-report",
        "expected_clamp": "none",
    },
    "T5": {
        "label": "adversarial empty target",
        "intent": "Score this file on engineering substance.",
        "target": str(EXP_ROOT / "fixtures/T5_empty.md"),
        "context": str(EXP_ROOT / "fixtures/T5_empty.md"),
        "target_type": "document",
        "expected_clamp": "no-evidence",
    },
}


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def prompt_hashes() -> dict[str, str]:
    return {
        "evidence_per_dim": sha256(_EVIDENCE_PROMPT_TEMPLATE),
        "evidence_batched": sha256(_BATCHED_EVIDENCE_PROMPT_TEMPLATE),
        "score_per_dim": sha256(_SCORE_PROMPT_TEMPLATE),
        "score_batched": sha256(_BATCHED_SCORE_PROMPT_TEMPLATE),
    }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def freeze_phase(targets: list[str], backend: str) -> None:
    base = frozen_dir(backend)
    base.mkdir(parents=True, exist_ok=True)
    for tid in targets:
        spec = TARGETS[tid]
        tdir = base / tid
        tdir.mkdir(exist_ok=True)
        rubric_path = tdir / "rubric.json"
        evidence_path = tdir / "evidence.json"
        if rubric_path.exists() and evidence_path.exists():
            print(f"[freeze] {tid}: cached, skipping", file=sys.stderr)
            continue

        print(f"[freeze] {tid}: synthesize + evidence", file=sys.stderr)
        target_content, resolved_target = read_target(spec["target"])
        context_content = read_context(spec["context"])

        rubric = synthesize(
            intent=spec["intent"],
            context_summary=context_content,
            target_type=spec["target_type"],
            backend=backend,
        )
        rubric_path.write_text(json.dumps(rubric, indent=2))

        evidence = collect_evidence(
            rubric=rubric,
            target_content=target_content,
            target_path=resolved_target,
            backend=backend,
            batch=False,
        )
        evidence_path.write_text(json.dumps(evidence, indent=2))
        # Also stash target excerpt for sub-exp B reproduction
        (tdir / "target.txt").write_text(target_content)
        print(f"[freeze] {tid}: rubric={len(rubric['dimensions'])} dims, "
              f"evidence={sum(1 for e in evidence if e.get('evidence_found'))} found",
              file=sys.stderr)


def load_frozen(tid: str, backend: str) -> tuple[dict, list[dict], str]:
    tdir = frozen_dir(backend) / tid
    rubric = json.loads((tdir / "rubric.json").read_text())
    evidence = json.loads((tdir / "evidence.json").read_text())
    target = (tdir / "target.txt").read_text()
    return rubric, evidence, target


def _run_score_only(tid: str, mode: str, rep: int, phase: str, backend: str) -> dict:
    rubric, evidence, _target = load_frozen(tid, backend)
    started = time.monotonic()
    started_iso = now_iso()
    fallback_used = False
    parse_failures = 0

    # Detect fallback by counting backend.call invocations
    real_call = backends_mod.call
    call_count = {"n": 0}

    def counting_call(prompt, backend=None):
        call_count["n"] += 1
        return real_call(prompt, backend=backend)

    backends_mod.call = counting_call
    try:
        scores = score_dimensions(
            rubric=rubric, evidence_list=evidence, backend=backend,
            batch=(mode == "batched"),
        )
    finally:
        backends_mod.call = real_call

    # If batched mode used > 1 call, batched parse failed and fell back to per-dim
    if mode == "batched" and call_count["n"] > 1:
        fallback_used = True

    aggregate = compute_aggregate(rubric=rubric, scores=scores)
    elapsed = time.monotonic() - started

    backend_label = backend
    model_id = None
    if backend == "claude-cli":
        backend_label = backends_mod.claude_cli_mode()
    elif backend == "dashscope-qwen":
        model_id = backends_mod.dashscope_model()
        backend_label = f"dashscope-{model_id}"
    elif backend == "google-gemini":
        model_id = backends_mod.gemini_model()
        backend_label = f"gemini-{model_id}"
    if mode == "batched":
        backend_label = f"{backend_label}+batch"

    return {
        "target_id": tid,
        "mode": mode,
        "sub_exp": phase,
        "rep": rep,
        "rubric_hash": sha256(json.dumps(rubric, sort_keys=True)),
        "evidence_hash": sha256(json.dumps(evidence, sort_keys=True)),
        "prompt_template_hashes": prompt_hashes(),
        "tool_version": __version__,
        "backend": backend,
        "backend_label": backend_label,
        "model_id": model_id,
        "started_at": started_iso,
        "ended_at": now_iso(),
        "latency_seconds": round(elapsed, 2),
        "n_backend_calls": call_count["n"],
        "scores": scores,
        "aggregate": aggregate["aggregate"],
        "dim_summaries": aggregate["dim_summaries"],
        "hedge_dims": aggregate["hedge_dims"],
        "fallback_used": fallback_used,
        "parse_failures": parse_failures,
    }


def _run_end_to_end(tid: str, mode: str, rep: int, phase: str, backend: str) -> dict:
    rubric, _frozen_evidence, target = load_frozen(tid, backend)
    started = time.monotonic()
    started_iso = now_iso()

    real_call = backends_mod.call
    call_count = {"n": 0}

    def counting_call(prompt, backend=None):
        call_count["n"] += 1
        return real_call(prompt, backend=backend)

    backends_mod.call = counting_call
    try:
        evidence = collect_evidence(
            rubric=rubric, target_content=target, target_path=tid,
            backend=backend, batch=(mode == "batched"),
        )
        scores = score_dimensions(
            rubric=rubric, evidence_list=evidence, backend=backend,
            batch=(mode == "batched"),
        )
    finally:
        backends_mod.call = real_call

    aggregate = compute_aggregate(rubric=rubric, scores=scores)
    elapsed = time.monotonic() - started

    expected_calls = 2 if mode == "batched" else 2 * len(rubric["dimensions"])
    fallback_used = (mode == "batched" and call_count["n"] > expected_calls)

    backend_label = backend
    model_id = None
    if backend == "claude-cli":
        backend_label = backends_mod.claude_cli_mode()
    elif backend == "dashscope-qwen":
        model_id = backends_mod.dashscope_model()
        backend_label = f"dashscope-{model_id}"
    elif backend == "google-gemini":
        model_id = backends_mod.gemini_model()
        backend_label = f"gemini-{model_id}"
    if mode == "batched":
        backend_label = f"{backend_label}+batch"

    return {
        "target_id": tid,
        "mode": mode,
        "sub_exp": phase,
        "rep": rep,
        "rubric_hash": sha256(json.dumps(rubric, sort_keys=True)),
        "evidence_hash": None,
        "prompt_template_hashes": prompt_hashes(),
        "tool_version": __version__,
        "backend": backend,
        "backend_label": backend_label,
        "model_id": model_id,
        "started_at": started_iso,
        "ended_at": now_iso(),
        "latency_seconds": round(elapsed, 2),
        "n_backend_calls": call_count["n"],
        "evidence": evidence,
        "scores": scores,
        "aggregate": aggregate["aggregate"],
        "dim_summaries": aggregate["dim_summaries"],
        "hedge_dims": aggregate["hedge_dims"],
        "fallback_used": fallback_used,
    }


def _write_run(run: dict, phase: str) -> Path:
    pdir = RUNS / phase
    pdir.mkdir(parents=True, exist_ok=True)
    ts = run["started_at"].replace(":", "").replace("-", "")[:15]
    fname = f"{run['target_id']}_{run['mode']}_rep{run['rep']}_{ts}.json"
    path = pdir / fname
    path.write_text(json.dumps(run, indent=2))
    _append_manifest(run, path)
    return path


def _append_manifest(run: dict, path: Path) -> None:
    new_file = not MANIFEST.exists()
    with MANIFEST.open("a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow([
                "target_id", "mode", "sub_exp", "rep", "aggregate",
                "fallback_used", "n_backend_calls", "latency_seconds",
                "tool_version", "backend_label", "started_at", "path"
            ])
        w.writerow([
            run["target_id"], run["mode"], run["sub_exp"], run["rep"],
            run["aggregate"], run["fallback_used"], run["n_backend_calls"],
            run["latency_seconds"], run["tool_version"], run["backend_label"],
            run["started_at"], str(path.relative_to(EXP_ROOT)),
        ])


def run_phase(phase: str, targets: list[str], n: int, backend: str) -> None:
    rng = random.Random(SEED)
    target_order = list(targets)
    rng.shuffle(target_order)

    runner = _run_end_to_end if phase.startswith("main_b") else _run_score_only

    for tid in target_order:
        # Alternate modes per rep within target to balance session drift
        for rep in range(n):
            modes_this_rep = ["per_dim", "batched"] if rep % 2 == 0 else ["batched", "per_dim"]
            for mode in modes_this_rep:
                print(f"[{phase}] {tid} {mode} rep{rep} ...", file=sys.stderr, end=" ", flush=True)
                run = runner(tid, mode, rep, phase, backend)
                path = _write_run(run, phase)
                print(f"agg={run['aggregate']} fb={run['fallback_used']} "
                      f"calls={run['n_backend_calls']} t={run['latency_seconds']}s "
                      f"-> {path.name}", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("phase", choices=["freeze", "pilot", "main_a", "main_b", "validate"])
    p.add_argument("--targets", default="all",
                   help="comma-separated target ids or 'all' (default: all). "
                        "pilot phase forces T1.")
    p.add_argument("--n", type=int, default=None,
                   help="reps per (target, mode); defaults: pilot=3, main_a=5, main_b=3, validate=3")
    p.add_argument("--backend", default="claude-cli",
                   choices=["claude-cli", "ollama-local", "dashscope-qwen", "google-gemini"])
    args = p.parse_args()

    if args.phase == "pilot":
        targets = ["T1"]
        n = args.n or 3
    elif args.phase == "validate":
        targets = ["T1", "T2", "T3", "T4", "T5"] if args.targets == "all" else args.targets.split(",")
        n = args.n or 3
    else:
        targets = ["T1", "T2", "T3", "T4", "T5"] if args.targets == "all" else args.targets.split(",")
        defaults = {"freeze": 1, "main_a": 5, "main_b": 3}
        n = args.n or defaults[args.phase]

    if args.phase == "freeze":
        freeze_phase(targets, args.backend)
        return

    # Ensure all requested targets are frozen
    missing = [t for t in targets if not (frozen_dir(args.backend) / t / "evidence.json").exists()]
    if missing:
        print(f"ERROR: targets not frozen yet: {missing}. Run `freeze` first.", file=sys.stderr)
        sys.exit(2)

    run_phase(args.phase, targets, n, args.backend)


if __name__ == "__main__":
    main()
