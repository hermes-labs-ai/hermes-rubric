"""hermes-rubric CLI entry point."""

import argparse
import sys
from pathlib import Path

from . import __version__
from .assessment import assess_path
from .errors import AssessmentError
from .preambles import SCOPE_CHOICES
from .synthesize import load_pinned


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
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument("--intent", default=None, help="One-sentence goal for the scoring (optional when --artifact-class or --pin-rubric is set)")
    parser.add_argument("--context", default=None, help="Path to context file(s) used for rubric synthesis (optional when --artifact-class or --pin-rubric is set)")
    parser.add_argument("--target", required=True, help="Path to file or directory to score")
    parser.add_argument("--target-type", default="document", help="Type label for the target (e.g. paper, tool, repo)")
    parser.add_argument("--out", default=None, help="Output JSON file path. Defaults to stdout.")
    parser.add_argument(
        "--backend",
        choices=[
            "claude-cli", "ollama-local", "dashscope-qwen",
            "google-gemini", "openai", "openai-sdk", "google-genai",
        ],
        default=None,
        help="Force a specific backend (default: auto-detect). Plugins registered "
             "via the `hermes_rubric.backends` entry-point group can also be used.",
    )
    parser.add_argument("--verbose", action="store_true", help="Print stage progress to stderr")
    parser.add_argument("--batch", action="store_true",
                        help="Batch evidence + score into one LLM call per stage. "
                             "Falls back to per-dim on parse failure or oversize prompt.")
    parser.add_argument("--target-window-bytes", type=int, default=8000,
                        help="Max bytes of target content visible during evidence collection. "
                            "Files exceeding this trigger a stderr warning. Default: 8000.")
    parser.add_argument("--context-window-bytes", type=int, default=8000,
                        help="Max bytes of context supplied to rubric synthesis. "
                             "Independent of --target-window-bytes. Default: 8000.")
    parser.add_argument("--scope-class", choices=list(SCOPE_CHOICES), default=None,
                        help="Tag the target's kind so the synthesizer judges it on "
                             "the right axes (gate-plan / sweep-plan / results-bundle). "
                             "Absorbs the hermes-rubric-blinded wrapper.")
    parser.add_argument("--intent-debias", action="store_true",
                        help="Prepend a debias preamble that neutralizes valence-loaded "
                             "framing in the intent (e.g. 'sound', 'ready', 'rigorous').")
    parser.add_argument("--artifact-class", default=None,
                        help="Use a deterministic class template for the rubric instead of "
                             "LLM synthesis. Available: social-post, show-hn-post, linkedin-post, "
                             "outreach-email, repo-readme. Stage 1 is bypassed; dim set is fixed "
                             "across runs.")
    parser.add_argument(
        "--pin-rubric",
        default=None,
        metavar="PATH",
        help="Score against a rubric from a prior JSON result. Stage 1 is bypassed "
             "and the rubric hash remains identical for comparable re-grades.",
    )

    args = parser.parse_args()

    if args.pin_rubric and args.artifact_class:
        parser.error("--pin-rubric and --artifact-class are mutually exclusive")

    pinned_rubric = None
    rubric_provenance = None
    if args.pin_rubric:
        try:
            pinned_rubric = load_pinned(args.pin_rubric)
        except (OSError, TypeError, ValueError) as exc:
            print(f"ERROR in Stage 1 (pinned rubric load): {exc}", file=sys.stderr)
            sys.exit(2)
        rubric_provenance = f"pinned:{args.pin_rubric}"
        if not args.intent:
            args.intent = pinned_rubric.get("rubric_intent")

    # Validate: synthesis needs intent and context; deterministic sources do not.
    if not args.artifact_class and not args.pin_rubric:
        if not args.intent:
            parser.error("--intent is required when --artifact-class/--pin-rubric is not set")
        if not args.context:
            parser.error("--context is required when --artifact-class/--pin-rubric is not set")
    else:
        # Deterministic rubric sources can use the target as evidence context.
        if not args.intent:
            args.intent = f"Score against the {args.artifact_class} class template."
        if not args.context:
            args.context = args.target  # use target as its own context for evidence collection

    def log(msg: str) -> None:
        if args.verbose:
            print(f"[hermes-rubric] {msg}", file=sys.stderr)

    try:
        result = assess_path(
            args.target,
            intent=args.intent,
            context_path=args.context,
            target_type=args.target_type,
            rubric=pinned_rubric,
            artifact_class=args.artifact_class,
            backend=args.backend,
            batch=args.batch,
            target_window_bytes=args.target_window_bytes,
            context_window_bytes=args.context_window_bytes,
            scope_class=args.scope_class,
            intent_debias=args.intent_debias,
            _progress=log,
            _rubric_provenance=rubric_provenance,
        )
    except AssessmentError as exc:
        if exc.stage in {"backend", "input"}:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)
        if exc.stage == "rubric":
            label = "class template load" if args.artifact_class else "rubric synthesis"
            print(f"ERROR in Stage 1 ({label}): {exc}", file=sys.stderr)
            sys.exit(2)
        if exc.stage == "evidence":
            print(f"ERROR in Stage 2 (evidence collection): {exc}", file=sys.stderr)
            sys.exit(3)
        label = "scoring" if exc.stage == "score" else exc.stage
        print(f"ERROR in Stage 3 ({label}): {exc}", file=sys.stderr)
        sys.exit(4)

    output_json = result.to_json()
    if args.out:
        out_path = Path(args.out).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_json)
        log(f"Output written to {out_path}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
