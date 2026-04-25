"""Cross-backend agreement metrics for hermes-rubric runs (G1).

Cohen's kappa quantifies inter-rater agreement above chance. Two
hermes-rubric runs against the same target — possibly using different
backends, prompts, or seeds — should agree on the per-dimension scores
if the rubric is reliable. Kappa near 1.0 = excellent reliability;
near 0 = chance; negative = systematic disagreement.

This is the load-bearing reliability proof for FLAGSHIP-SPEC §G9.

Implementation notes
--------------------
- Scores are binned to integer 0-10 (Cohen's kappa requires
  categorical/ordinal ratings). Sub-integer differences inside the
  same bin are treated as agreement.
- Dimensions are matched by ``dim_name`` (the human-meaningful key);
  ``dim_id`` is synthesizer-local and not stable across runs.
- Mismatched dimensions emit a stderr warning and are dropped from
  the kappa computation. Only matched dimensions are returned.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _bin_score(score: float | int) -> int:
    """Bin a 0-10 score to integer category. Clamp out-of-range values."""
    try:
        v = int(round(float(score)))
    except (TypeError, ValueError):
        raise ValueError(f"Non-numeric score: {score!r}")
    if v < 0:
        return 0
    if v > 10:
        return 10
    return v


def _scores_by_name(run: dict[str, Any]) -> dict[str, int]:
    """Extract {dim_name: binned_score} from a hermes-rubric run dict."""
    out: dict[str, int] = {}
    for entry in run.get("per_dim_scores", []):
        if not isinstance(entry, dict):
            continue
        name = entry.get("dim_name") or entry.get("name")
        if not name:
            continue
        if "score" not in entry:
            continue
        out[name] = _bin_score(entry["score"])
    return out


def _pairwise_kappa(a: list[int], b: list[int], categories: int = 11) -> float:
    """Cohen's kappa for two ordinal rater sequences over 0..categories-1.

    Identical sequences -> 1.0. Independent random raters -> ~0.0.
    Systematic disagreement -> negative.

    Edge case: if both raters give a single category for every item
    (po=1.0, pe=1.0), kappa is undefined. We return 1.0 (perfect
    agreement) since there is no disagreement to measure.
    """
    if len(a) != len(b):
        raise ValueError(f"Length mismatch: {len(a)} vs {len(b)}")
    n = len(a)
    if n == 0:
        raise ValueError("Cannot compute kappa over zero items")

    # Observed agreement
    agree = sum(1 for x, y in zip(a, b) if x == y)
    po = agree / n

    # Expected agreement by chance: sum over categories of P(rater1=k)*P(rater2=k)
    counts_a = [0] * categories
    counts_b = [0] * categories
    for x in a:
        counts_a[x] += 1
    for y in b:
        counts_b[y] += 1
    pe = sum((counts_a[k] / n) * (counts_b[k] / n) for k in range(categories))

    if pe >= 1.0:
        # Both raters used a single category — by convention kappa=1.0 if
        # po==1.0 (they agreed) else 0.0 (they used the same single bucket
        # but that's vacuous).
        return 1.0 if po >= 1.0 else 0.0
    return (po - pe) / (1.0 - pe)


def cohens_kappa(
    run1: dict[str, Any],
    run2: dict[str, Any],
    *,
    warn_stream=sys.stderr,
) -> dict[str, Any]:
    """Compute Cohen's kappa between two hermes-rubric runs.

    Returns a dict with:
      - ``per_dimension``: list of {dim_name, score_run1, score_run2} for
        each matched dimension (kappa is a corpus-level metric, but we
        surface the matched pairs so callers can inspect disagreement).
      - ``mean_kappa``: corpus-level Cohen's kappa across matched dims.
      - ``matched_dims``: count of dimensions present in both runs.
      - ``unmatched_run1`` / ``unmatched_run2``: dim_names present in one
        run but not the other. A non-empty list emits a stderr warning.
      - ``categories``: 11 (0..10 integer bins).
    """
    s1 = _scores_by_name(run1)
    s2 = _scores_by_name(run2)

    matched = sorted(set(s1.keys()) & set(s2.keys()))
    only1 = sorted(set(s1.keys()) - set(s2.keys()))
    only2 = sorted(set(s2.keys()) - set(s1.keys()))

    if (only1 or only2) and warn_stream is not None:
        warn_stream.write(
            "[hermes-rubric] WARNING: rubric dimensions differ between runs — "
            f"{len(matched)} matched, {len(only1)} only in run1, "
            f"{len(only2)} only in run2. Kappa computed over matched dims only.\n"
        )

    if not matched:
        raise ValueError(
            "No matching dimensions between runs. Cohen's kappa requires "
            "at least one shared dim_name."
        )

    a = [s1[name] for name in matched]
    b = [s2[name] for name in matched]
    kappa = _pairwise_kappa(a, b)

    per_dim = [
        {"dim_name": name, "score_run1": s1[name], "score_run2": s2[name]}
        for name in matched
    ]

    return {
        "mean_kappa": round(kappa, 4),
        "matched_dims": len(matched),
        "unmatched_run1": only1,
        "unmatched_run2": only2,
        "per_dimension": per_dim,
        "categories": 11,
    }


def kappa_from_paths(run1_path: str, run2_path: str) -> dict[str, Any]:
    """Load two hermes-rubric JSON outputs and compute their kappa."""
    r1 = json.loads(Path(run1_path).expanduser().read_text())
    r2 = json.loads(Path(run2_path).expanduser().read_text())
    return cohens_kappa(r1, r2)


def main(argv: list[str] | None = None) -> int:
    """`hermes-rubric kappa` subcommand entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="hermes-rubric kappa",
        description="Cohen's kappa between two hermes-rubric runs.",
    )
    parser.add_argument("--run1", required=True, help="First run's JSON output")
    parser.add_argument("--run2", required=True, help="Second run's JSON output")
    parser.add_argument("--out", default=None, help="Write kappa report JSON here (default: stdout)")
    args = parser.parse_args(argv)

    try:
        report = kappa_from_paths(args.run1, args.run2)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    payload = json.dumps(report, indent=2)
    if args.out:
        out_path = Path(args.out).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
