"""Compute Cohen's kappa between batched and per_dim modes on existing runs.

Reads runs/main_a/*.json and runs/main_b/*.json, dedupes by latest started_at
per (target, mode, rep), pairs by (target, rep, backend), and computes kappa
across modes via hermes_rubric.agreement._pairwise_kappa.

Bins scores to integer 0-10. Match dims by dim_name (per agreement.py policy).
Reports per-backend, per-target, and overall kappa.
"""

from __future__ import annotations

import glob
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

# Use the agreement module's binning + kappa
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from hermes_rubric.agreement import _bin_score, _pairwise_kappa


def load_runs(phase: str) -> list[dict]:
    return [json.loads(open(f).read())
            for f in glob.glob(f"experiments/batch-equiv-2026-04-25/runs/{phase}/*.json")]


def dedupe_latest(runs: list[dict]) -> list[dict]:
    latest: dict[tuple[str, str, str, int], dict] = {}
    for r in runs:
        backend_kind = "claude" if "claude" in r["backend_label"] else \
                       "qwen" if "qwen" in r["backend_label"] else \
                       "gemini" if "gemini" in r["backend_label"] else \
                       "openai" if "openai" in r["backend_label"] else "other"
        k = (backend_kind, r["target_id"], r["mode"], r["rep"])
        if k not in latest or r["started_at"] > latest[k]["started_at"]:
            latest[k] = r
    return list(latest.values())


def scores_by_dim(run: dict) -> dict[str, int]:
    """Extract {dim_id: binned_score} from a runner.py run record."""
    out: dict[str, int] = {}
    for s in run.get("scores", []):
        if not isinstance(s, dict):
            continue
        # Use dim_id as the key; within a single (target, rep) pair the rubric is
        # frozen, so dim_ids align across modes (no rubric noise to worry about).
        if "dim_id" not in s or "score" not in s:
            continue
        try:
            out[s["dim_id"]] = _bin_score(s["score"])
        except ValueError:
            continue
    return out


def main() -> None:
    all_runs = load_runs("main_a") + load_runs("main_b")
    runs = dedupe_latest(all_runs)

    # Group by (backend, target, rep) -> mode -> {dim_id: score}
    grouped: dict[tuple[str, str, int], dict[str, dict[str, int]]] = defaultdict(dict)
    backend_for_run: dict[tuple[str, str, int], str] = {}
    for r in runs:
        backend_kind = "claude" if "claude" in r["backend_label"] else \
                       "qwen" if "qwen" in r["backend_label"] else \
                       "gemini" if "gemini" in r["backend_label"] else \
                       "openai" if "openai" in r["backend_label"] else "other"
        key = (backend_kind, r["target_id"], r["rep"])
        grouped[key][r["mode"]] = scores_by_dim(r)
        backend_for_run[key] = backend_kind

    # Per-pair kappas
    pair_kappas: dict[tuple[str, str], list[float]] = defaultdict(list)
    for key, modes in grouped.items():
        if "per_dim" not in modes or "batched" not in modes:
            continue
        per = modes["per_dim"]
        bat = modes["batched"]
        common = sorted(set(per) & set(bat))
        if len(common) < 2:
            continue
        a = [per[d] for d in common]
        b = [bat[d] for d in common]
        if a == b:
            kappa = 1.0
        else:
            kappa = _pairwise_kappa(a, b)
        backend, tid, rep = key
        pair_kappas[(backend, tid)].append(kappa)

    # Aggregate by backend/target
    print("=== Cohen's kappa: per_dim vs batched (paired by target+rep) ===\n")
    print(f"{'backend':<10} {'target':<6} {'n_pairs':>8} {'mean_kappa':>12} {'min_kappa':>11} {'max_kappa':>11}")
    print("-" * 60)

    by_backend: dict[str, list[float]] = defaultdict(list)
    for (backend, tid), ks in sorted(pair_kappas.items()):
        if not ks:
            continue
        m = statistics.mean(ks)
        print(f"{backend:<10} {tid:<6} {len(ks):>8d} {m:>12.4f} {min(ks):>11.4f} {max(ks):>11.4f}")
        by_backend[backend].extend(ks)

    print()
    print("=== Per-backend overall ===\n")
    print(f"{'backend':<10} {'n_pairs':>8} {'mean_kappa':>12} {'pct_kappa>=0.6':>15}")
    print("-" * 50)
    for backend, ks in sorted(by_backend.items()):
        m = statistics.mean(ks)
        pct = 100 * sum(1 for k in ks if k >= 0.6) / len(ks)
        print(f"{backend:<10} {len(ks):>8d} {m:>12.4f} {pct:>14.1f}%")

    print()
    overall = [k for ks in by_backend.values() for k in ks]
    if overall:
        m = statistics.mean(overall)
        pct = 100 * sum(1 for k in overall if k >= 0.6) / len(overall)
        print(f"OVERALL    n={len(overall)}  mean κ={m:.4f}  pct(κ≥0.6)={pct:.1f}%")
        gate = "✓ PASS" if m >= 0.6 else "✗ FAIL"
        print(f"\nPre-registered gate: mean κ ≥ 0.6 across all paired comparisons. {gate}")


if __name__ == "__main__":
    main()
