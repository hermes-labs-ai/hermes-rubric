"""Generate 5 same-input synthesized rubrics for V2 (Mission C).

Run from repo root:
    python applied/mission-C-20260429/_v2_synth_rubrics.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

OUT = Path(__file__).parent / "V2-rubrics"
OUT.mkdir(exist_ok=True)

INTENT = "audit this paper for epistemic accountability and hygiene"
TARGET_TYPE = "preprint-paper"
CONTEXT = (
    "META-RUBRIC: a structured rubric tool for auditing AI-system claims. "
    "Source-class evidence weighting; cap-at-6 on README-only citations; "
    "preprint-paper policy lifts caps when prose is the ground truth."
)
TARGET_EXCERPT = (
    "We propose META-RUBRIC, a structured rubric synthesizer that generates "
    "evaluation dimensions per (intent, context, target-type). Evidence is "
    "source-classed (code, test, config, doc, readme, other) and a "
    "self-marketing cap (max=6) applies when all citations are doc/readme. "
    "Preprint-paper policy lifts the cap when prose is ground truth."
)


def main() -> int:
    from hermes_rubric.synthesize import synthesize

    n_target = 5
    t0 = time.time()
    for i in range(1, n_target + 1):
        out_path = OUT / f"run-{i}.json"
        if out_path.is_file():
            print(f"[skip] {out_path} exists", file=sys.stderr)
            continue
        try:
            rubric = synthesize(
                intent=INTENT,
                context_summary=CONTEXT,
                target_type=TARGET_TYPE,
                backend=None,  # auto-detect
                scope_class=None,
                intent_debias=False,
                target_excerpt=TARGET_EXCERPT,
            )
        except Exception as e:
            print(f"[err run-{i}] {e!r}", file=sys.stderr)
            return 2
        out_path.write_text(json.dumps(rubric, indent=2))
        print(f"[ok] run-{i}: {len(rubric.get('dimensions', []))} dims "
              f"({time.time()-t0:.1f}s elapsed)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
