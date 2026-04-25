"""hermes-rubric CLI entry point."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from hermes_blind import SCOPE_CHOICES

from . import backends
from .evidence import collect_evidence, read_context, read_target
from .receipt import build_receipt
from .score import compute_aggregate, score_dimensions
from .synthesize import synthesize


def main() -> None:
    # Subcommand routing. The default ("score" — no subcommand) preserves
    # the v0.1.x argv shape exactly. Today only `kappa` is dispatched out.
    if len(sys.argv) > 1 and sys.argv[1] == "kappa":
        from . import agreement
        sys.exit(agreement.main(sys.argv[2:]))

    parser = argparse.ArgumentParser(
        prog="hermes-rubric",
        description="Evidence-first structured scoring. Synthesizes rubric, collects evidence, then scores.",
    )
    parser.add_argument("--intent", required=True, help="One-sentence goal for the scoring")
    parser.add_argument("--context", required=True, help="Path to context file(s) used for rubric synthesis")
    parser.add_argument("--target", required=True, help="Path to file or directory to score")
    parser.add_argument("--target-type", default="document", help="Type label for the target (e.g. paper, tool, repo)")
    parser.add_argument("--out", default=None, help="Output JSON file path. Defaults to stdout.")
    parser.add_argument("--backend", choices=["claude-cli", "ollama-local", "dashscope-qwen", "google-gemini"], default=None,
                        help="Force a specific backend (default: auto-detect)")
    parser.add_argument("--verbose", action="store_true", help="Print stage progress to stderr")
    parser.add_argument("--batch", action="store_true",
                        help="Batch evidence + score into one LLM call per stage. "
                             "Falls back to per-dim on parse failure or oversize prompt.")
    parser.add_argument("--target-window-bytes", type=int, default=8000,
                        help="Max bytes of target/context content visible to the rubric. "
                             "Files exceeding this trigger a stderr warning. Default: 8000.")
    parser.add_argument("--scope-class", choices=list(SCOPE_CHOICES), default=None,
                        help="Tag the target's kind so the synthesizer judges it on "
                             "the right axes (gate-plan / sweep-plan / results-bundle). "
                             "Absorbs the hermes-rubric-blinded wrapper.")
    parser.add_argument("--intent-debias", action="store_true",
                        help="Prepend a debias preamble that neutralizes valence-loaded "
                             "framing in the intent (e.g. 'sound', 'ready', 'rigorous').")

    args = parser.parse_args()

    def log(msg: str) -> None:
        if args.verbose:
            print(f"[hermes-rubric] {msg}", file=sys.stderr)

    # Auto-detect backend
    try:
        backend = args.backend or backends.detect()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    log(f"backend: {backend}")

    # Read inputs
    try:
        target_content, resolved_target = read_target(args.target, window_bytes=args.target_window_bytes)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    context_content = read_context(args.context, window_bytes=args.target_window_bytes)
    log(f"target: {resolved_target} ({len(target_content)} chars)")
    log(f"context: {args.context} ({len(context_content)} chars)")

    # Stage 1: Synthesize rubric
    log("Stage 1: synthesizing rubric...")
    try:
        rubric = synthesize(
            intent=args.intent,
            context_summary=context_content,
            target_type=args.target_type,
            backend=backend,
            scope_class=args.scope_class,
            intent_debias=args.intent_debias,
        )
    except Exception as e:
        print(f"ERROR in Stage 1 (rubric synthesis): {e}", file=sys.stderr)
        sys.exit(2)
    log(f"  rubric: {len(rubric['dimensions'])} dimensions")

    # Stage 2: Collect evidence
    log("Stage 2: collecting evidence...")
    try:
        evidence_list = collect_evidence(
            rubric=rubric,
            target_content=target_content,
            target_path=resolved_target,
            backend=backend,
            batch=args.batch,
        )
    except Exception as e:
        print(f"ERROR in Stage 2 (evidence collection): {e}", file=sys.stderr)
        sys.exit(3)
    hedge_count = sum(1 for ev in evidence_list if ev.get("hedge"))
    log(f"  evidence: {len(evidence_list)} dimensions, {hedge_count} hedged")

    # Stage 3: Score
    log("Stage 3: scoring dimensions...")
    try:
        scores = score_dimensions(rubric=rubric, evidence_list=evidence_list, backend=backend, batch=args.batch)
        aggregate_data = compute_aggregate(rubric=rubric, scores=scores)
    except Exception as e:
        print(f"ERROR in Stage 3 (scoring): {e}", file=sys.stderr)
        sys.exit(4)
    log(f"  aggregate: {aggregate_data['aggregate']}/10")

    # Build receipt — surface claude-cli mode (bare vs contextual) so
    # downstream readers know whether the score was context-compensated.
    backend_label = backend
    if backend == "claude-cli":
        backend_label = backends.claude_cli_mode()
    if args.batch:
        backend_label = f"{backend_label}+batch"
    receipt = build_receipt(
        intent=args.intent,
        context_path=args.context,
        target_path=args.target,
        backend=backend_label,
        rubric=rubric,
        evidence_list=evidence_list,
        scores=scores,
        target_content=target_content,
        context_content=context_content,
    )

    # Assemble output
    output: dict[str, Any] = {
        "rubric": rubric,
        "evidence_citations": evidence_list,
        "per_dim_scores": scores,
        "aggregate": aggregate_data["aggregate"],
        "max_possible": 10.0,
        "hedge_dims": aggregate_data["hedge_dims"],
        "hedge_note": aggregate_data["hedge_note"],
        "dim_summaries": aggregate_data["dim_summaries"],
        "receipt": receipt,
    }

    # Write output
    output_json = json.dumps(output, indent=2)
    if args.out:
        out_path = Path(args.out).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_json)
        log(f"Output written to {out_path}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
