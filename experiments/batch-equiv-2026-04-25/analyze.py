"""Analysis of runs/. Loads all run JSONs, computes deltas, prints summary.

Mixed-effects model is parked behind an optional `--mixed` flag because
statsmodels is not a hard dependency of hermes-rubric.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

EXP_ROOT = Path(__file__).parent
RUNS = EXP_ROOT / "runs"


def load_runs(phase: str | None = None) -> list[dict]:
    runs = []
    base = RUNS / phase if phase else RUNS
    if not base.exists():
        return runs
    for f in sorted(base.rglob("*.json")):
        runs.append(json.loads(f.read_text()))
    return runs


def aggregate_summary(runs: list[dict]) -> dict:
    by_mode = defaultdict(list)
    by_target_mode = defaultdict(list)
    fallbacks = defaultdict(int)
    latencies = defaultdict(list)
    calls = defaultdict(list)

    for r in runs:
        by_mode[r["mode"]].append(r["aggregate"])
        by_target_mode[(r["target_id"], r["mode"])].append(r["aggregate"])
        if r.get("fallback_used"):
            fallbacks[r["mode"]] += 1
        latencies[r["mode"]].append(r["latency_seconds"])
        calls[r["mode"]].append(r["n_backend_calls"])

    out = {}
    for mode, vals in by_mode.items():
        out[mode] = {
            "n": len(vals),
            "mean_agg": round(statistics.mean(vals), 3),
            "stdev_agg": round(statistics.stdev(vals), 3) if len(vals) > 1 else 0.0,
            "mean_latency_s": round(statistics.mean(latencies[mode]), 2),
            "mean_calls": round(statistics.mean(calls[mode]), 2),
            "fallback_count": fallbacks[mode],
            "fallback_rate": round(fallbacks[mode] / len(vals), 3),
        }
    return out, by_target_mode


def per_dim_deltas(runs: list[dict]) -> dict:
    """For each (target, dim_id, rep) find the paired per_dim/batched scores
    across runs, compute deltas. Returns per-dim distribution stats.
    """
    # Group by (target, rep) → mode → {dim_id: score}
    grouped = defaultdict(lambda: defaultdict(dict))
    for r in runs:
        key = (r["target_id"], r["rep"])
        for s in r["scores"]:
            grouped[key][r["mode"]][s["dim_id"]] = s["score"]

    deltas_by_dim = defaultdict(list)
    for (tid, rep), modes in grouped.items():
        if "per_dim" not in modes or "batched" not in modes:
            continue
        for dim_id, s_per in modes["per_dim"].items():
            if dim_id in modes["batched"]:
                delta = modes["batched"][dim_id] - s_per
                deltas_by_dim[dim_id].append(delta)

    summary = {}
    for dim_id, deltas in deltas_by_dim.items():
        summary[dim_id] = {
            "n": len(deltas),
            "mean_delta": round(statistics.mean(deltas), 3),
            "stdev_delta": round(statistics.stdev(deltas), 3) if len(deltas) > 1 else 0.0,
            "max_abs_delta": round(max(abs(d) for d in deltas), 3),
        }
    return summary


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--phase", default=None,
                   help="filter to runs/<phase>/ only (e.g. pilot, main_a)")
    args = p.parse_args()

    runs = load_runs(args.phase)
    if not runs:
        print("no runs found")
        return

    print(f"=== {len(runs)} runs loaded" + (f" (phase={args.phase})" if args.phase else "") + " ===\n")

    mode_summary, by_target_mode = aggregate_summary(runs)
    print("--- Per-mode aggregate summary ---")
    for mode, stats in mode_summary.items():
        print(f"  {mode:10s}  n={stats['n']:3d}  mean={stats['mean_agg']:.3f}  "
              f"σ={stats['stdev_agg']:.3f}  latency={stats['mean_latency_s']:.1f}s  "
              f"calls={stats['mean_calls']:.1f}  fallback={stats['fallback_count']}/{stats['n']}")

    print("\n--- Per-target paired aggregate ---")
    targets = sorted({tid for tid, _ in by_target_mode})
    for tid in targets:
        per = by_target_mode.get((tid, "per_dim"), [])
        bat = by_target_mode.get((tid, "batched"), [])
        if per and bat:
            d = statistics.mean(bat) - statistics.mean(per)
            print(f"  {tid}  per_dim_mean={statistics.mean(per):.3f}  "
                  f"batched_mean={statistics.mean(bat):.3f}  delta={d:+.3f}")

    print("\n--- Per-dim deltas (batched - per_dim) ---")
    deltas = per_dim_deltas(runs)
    for dim_id, s in sorted(deltas.items()):
        print(f"  {dim_id:30s}  n={s['n']:3d}  mean_Δ={s['mean_delta']:+.3f}  "
              f"σ_Δ={s['stdev_delta']:.3f}  max|Δ|={s['max_abs_delta']:.3f}")

    print("\n--- Pre-registered acceptance check ---")
    overall_per = mode_summary.get("per_dim", {})
    overall_bat = mode_summary.get("batched", {})
    if overall_per and overall_bat:
        agg_delta = overall_bat["mean_agg"] - overall_per["mean_agg"]
        agg_sigma = max(overall_per["stdev_agg"], overall_bat["stdev_agg"])
        max_dim_delta = max((s["max_abs_delta"] for s in deltas.values()), default=0.0)
        print(f"  aggregate Δ:        {agg_delta:+.3f}  (target |Δ|<1.0)  "
              f"{'✓' if abs(agg_delta) < 1.0 else '✗'}")
        print(f"  σ̂ (aggregate):      {agg_sigma:.3f}  (pilot abort if >1.5)  "
              f"{'✓' if agg_sigma < 1.5 else '✗'}")
        print(f"  max |per-dim Δ|:    {max_dim_delta:.3f}  (target <2.0)  "
              f"{'✓' if max_dim_delta < 2.0 else '✗'}")
        print(f"  batched fallback:   {overall_bat['fallback_rate']:.1%}  (target <10%)  "
              f"{'✓' if overall_bat['fallback_rate'] < 0.10 else '✗'}")

    print()


if __name__ == "__main__":
    main()
