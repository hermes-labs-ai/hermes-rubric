"""V2 Hungarian-matched cosine analysis (Mission C).

Loads V2-rubrics/run-{1..5}.json, embeds each dim via Ollama nomic-embed-text,
computes pairwise Hungarian-matched cosine, builds random-permutation null,
runs Constraint-2 sanity check, writes V2-results.json.

Run from repo root:
    python applied/mission-C-20260429/_v2_analysis.py
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import urllib.request
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

HERE = Path(__file__).parent
RUBRICS_DIR = HERE / "V2-rubrics"
EMB_CACHE = HERE / "_v2_emb_cache.json"
OUT = HERE / "V2-results.json"
HALT_LOG = HERE / "V2-halt-log.md"

OLLAMA_URL = "http://localhost:11434/api/embeddings"
EMB_MODEL = "nomic-embed-text"

# Reproducibility
random.seed(20260429)
np.random.seed(20260429)
N_NULL = 200


def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _load_cache() -> dict:
    if EMB_CACHE.is_file():
        return json.loads(EMB_CACHE.read_text())
    return {}


def _save_cache(c: dict) -> None:
    EMB_CACHE.write_text(json.dumps(c))


def embed(text: str, cache: dict) -> np.ndarray:
    key = _h(text)
    if key in cache:
        return np.array(cache[key], dtype=np.float64)
    payload = json.dumps({"model": EMB_MODEL, "prompt": text}).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.loads(resp.read())
    vec = body["embedding"]
    cache[key] = vec
    return np.array(vec, dtype=np.float64)


def dim_text(d: dict) -> str:
    return f"{d.get('name','')}. {d.get('description','')} {d.get('evidence_instructions','')}".strip()


def cosine_matrix(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """A: (m, d), B: (n, d) → (m, n) cosine matrix."""
    An = A / (np.linalg.norm(A, axis=1, keepdims=True) + 1e-12)
    Bn = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-12)
    return An @ Bn.T


def hungarian_score(A: np.ndarray, B: np.ndarray) -> float:
    M = cosine_matrix(A, B)
    row, col = linear_sum_assignment(-M)
    n = min(A.shape[0], B.shape[0])
    return float(M[row, col].sum() / n)


def main() -> int:
    rubrics = []
    for i in range(1, 6):
        p = RUBRICS_DIR / f"run-{i}.json"
        if not p.is_file():
            print(f"missing: {p}", file=sys.stderr)
            return 2
        rubrics.append(json.loads(p.read_text()))

    print(f"loaded {len(rubrics)} rubrics; dim counts: "
          f"{[len(r.get('dimensions',[])) for r in rubrics]}", file=sys.stderr)

    # Embed all dims
    cache = _load_cache()
    embedded = []  # list of (m_k, 768) matrices
    for k, r in enumerate(rubrics, start=1):
        dims = r.get("dimensions", [])
        vecs = []
        for d in dims:
            v = embed(dim_text(d), cache)
            vecs.append(v)
        embedded.append(np.stack(vecs))
        print(f"embedded run-{k}: shape={embedded[-1].shape}", file=sys.stderr)
    _save_cache(cache)

    # Same-input distribution: all C(5,2) = 10 pairs
    same_pairs = []
    for a, b in combinations(range(len(embedded)), 2):
        h = hungarian_score(embedded[a], embedded[b])
        same_pairs.append({"a": a + 1, "b": b + 1, "H": h})
    print(f"same-input pairs: n={len(same_pairs)}, "
          f"min={min(p['H'] for p in same_pairs):.4f}, "
          f"max={max(p['H'] for p in same_pairs):.4f}, "
          f"mean={np.mean([p['H'] for p in same_pairs]):.4f}", file=sys.stderr)

    # Random-permutation null: pool all dims, sample N_NULL random rubric pairs
    pool = []
    for E in embedded:
        for row in E:
            pool.append(row)
    pool = np.stack(pool)
    print(f"pool size: {pool.shape[0]} dims", file=sys.stderr)

    m_bar = int(round(np.mean([E.shape[0] for E in embedded])))
    print(f"m_bar (mean dims per rubric): {m_bar}", file=sys.stderr)

    null_scores = []
    for _ in range(N_NULL):
        idx = random.sample(range(pool.shape[0]), 2 * m_bar)
        A = pool[idx[:m_bar]]
        B = pool[idx[m_bar:]]
        null_scores.append(hungarian_score(A, B))
    null_scores = np.array(null_scores)

    null_mean = float(null_scores.mean())
    null_std = float(null_scores.std(ddof=1))
    threshold = null_mean + 2 * null_std
    pct = {
        "p25": float(np.percentile(null_scores, 25)),
        "p50": float(np.percentile(null_scores, 50)),
        "p75": float(np.percentile(null_scores, 75)),
        "p95": float(np.percentile(null_scores, 95)),
        "p97_5": float(np.percentile(null_scores, 97.5)),
    }

    # Constraint-2 sanity check
    sanity_pass = 0.30 <= threshold <= 0.95
    sanity_regime = (
        "discriminating" if sanity_pass
        else ("low_domain_resolution" if threshold < 0.30 else "high_domain_resolution")
    )

    # Pass criterion (all same-input ≥ max(0.7, threshold)) AND sanity
    abs_floor = 0.70
    effective_thr = max(abs_floor, threshold)
    same_min = min(p["H"] for p in same_pairs)
    pass_same = same_min >= effective_thr
    overall_pass = sanity_pass and pass_same

    result = {
        "experiment": "V2 Hungarian-matched cosine on rubric-dim embeddings",
        "embedding_model": EMB_MODEL,
        "n_rubrics": len(rubrics),
        "dim_counts": [E.shape[0] for E in embedded],
        "n_same_input_pairs": len(same_pairs),
        "same_input_pairs": same_pairs,
        "same_input_summary": {
            "min": float(min(p["H"] for p in same_pairs)),
            "max": float(max(p["H"] for p in same_pairs)),
            "mean": float(np.mean([p["H"] for p in same_pairs])),
            "std": float(np.std([p["H"] for p in same_pairs], ddof=1)),
        },
        "null": {
            "n": int(N_NULL),
            "m_bar": int(m_bar),
            "pool_size": int(pool.shape[0]),
            "mean": null_mean,
            "std": null_std,
            "min": float(null_scores.min()),
            "max": float(null_scores.max()),
            "percentiles": pct,
            "samples_first_10": [float(x) for x in null_scores[:10]],
        },
        "threshold_2sigma": float(threshold),
        "absolute_floor": abs_floor,
        "effective_threshold": float(effective_thr),
        "sanity": {
            "pass": sanity_pass,
            "regime": sanity_regime,
            "rule": "0.30 <= threshold <= 0.95 → discriminating",
        },
        "same_input_min_ge_threshold": pass_same,
        "overall_pass": overall_pass,
        "seeds": {"random": 20260429, "numpy": 20260429},
    }
    OUT.write_text(json.dumps(result, indent=2))
    print(f"wrote {OUT}", file=sys.stderr)

    # Halt log if sanity fails
    if not sanity_pass:
        HALT_LOG.write_text(
            f"# V2 HALT — Sanity Check Failed\n\n"
            f"**Threshold:** {threshold:.4f}\n"
            f"**Regime:** {sanity_regime}\n"
            f"**Null mean:** {null_mean:.4f}\n"
            f"**Null std:** {null_std:.4f}\n"
            f"**Null percentiles:** {pct}\n\n"
            f"Per Constraint 2 sanity rule (0.30 ≤ threshold ≤ 0.95), this V2 result is "
            f"NOT used to validate same-input rubric stability. Embedding-space bias may "
            f"have substituted for LLM-judge bias. V2 is logged as failed-component for "
            f"Phase 1 self-rubric.\n"
        )
        print(f"HALT — wrote {HALT_LOG}", file=sys.stderr)

    print("\n=== V2 SUMMARY ===")
    print(f"  same-input min:     {result['same_input_summary']['min']:.4f}")
    print(f"  same-input mean:    {result['same_input_summary']['mean']:.4f}")
    print(f"  null mean ± 2std:   {null_mean:.4f} ± {2*null_std:.4f}")
    print(f"  threshold (2σ):     {threshold:.4f}")
    print(f"  effective thr:      {effective_thr:.4f}")
    print(f"  sanity:             {'PASS' if sanity_pass else 'HALT'} ({sanity_regime})")
    print(f"  same-input pass:    {pass_same}")
    print(f"  overall:            {'PASS' if overall_pass else 'FAIL/HALT'}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
