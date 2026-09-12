# Quickstart

## Install

```bash
pip install hermes-rubric==1.2.2
hermes-rubric --version
```

The pin is the release this page was verified against; drop it to take the
latest. `--version` prints `hermes-rubric 1.2.2` — the string is built from
`__version__` in `src/hermes_rubric/__init__.py` — and proves the install. It
does not exercise an assessment: every score on this page comes from a backend
call.

## Pick a backend explicitly

Scoring needs a model backend. Automatic selection prefers an authenticated
Claude Code CLI, then a running local Ollama; cloud backends are never
auto-selected — see `detect()` in `src/hermes_rubric/backends.py`, which
returns only those two. Pass `--backend` (or `backend=`) anyway, so a recipe you paste
into CI cannot silently pick a different backend, transmit your target
somewhere you did not intend, or spend money.

| Backend | Prerequisite | Where the target goes |
|---|---|---|
| `ollama-local` | `ollama serve` running on `localhost:11434` with one of `qwen3.5:14b`, `gemma3:12b`, `gemma3:4b`, `mistral:7b`, `qwen3.5:9b`, `qwen3.5:4b` pulled — port and model list from `_OLLAMA_DEFAULT_MODEL` / `_OLLAMA_FALLBACK_MODELS` and `_ollama_model()` in `src/hermes_rubric/backends.py` | stays on your machine |
| `claude-cli` | `claude` on `PATH` and already signed in | Anthropic |
| `openai-sdk` | `pip install "hermes-rubric[openai]"` and `OPENAI_API_KEY` set | OpenAI |

If none of these is available, stop here. `hermes-rubric` has no offline
scoring mode, and a run without a backend fails rather than inventing a score.

## Run one complete synthetic assessment

Everything below is self-contained — no repository checkout, no file you have
to supply, no undefined variable.

```bash
workdir="$(mktemp -d)"
trap 'rm -rf -- "$workdir"' EXIT

cat > "$workdir/post.md" <<'EOF'
We rebuilt our ingest pipeline and it is now 40% faster.

The old path re-parsed every record twice. We removed the second
parse and batched the writes. Numbers come from the benchmark in
bench/ingest_bench.py, run on the same 10k-record fixture before
and after (12.4s -> 7.4s, median of 5 runs).

Caveat: we only measured the JSON ingest path. The CSV path is
unchanged and was not benchmarked.
EOF

hermes-rubric \
  --artifact-class social-post \
  --target "$workdir/post.md" \
  --backend ollama-local \
  --out "$workdir/result.json" \
  --verbose
```

`mktemp -d` gives this run a private directory instead of a guessable name in
shared `/tmp`, so another user on the same machine cannot pre-create or swap the
files you are about to write and read; the `trap` deletes it when the shell
exits. Every path is quoted, because `mktemp -d` may return a name containing
spaces. Run the read-back block below in the same shell, before that shell
exits.

`--artifact-class social-post` loads a bundled rubric instead of
synthesizing one — its nine dimensions are defined in
`src/hermes_rubric/classes/social-post.yaml` — so Stage 1 is skipped and the
dimension set and `stage_1_rubric_hash_sha256` are identical across runs. That
makes *rubric selection* deterministic. It does not make the scores
deterministic. They are model output, and this recipe pins no decoding
parameters: `_call_ollama()` in `src/hermes_rubric/backends.py` sends only
`num_predict`, no `temperature` and no `seed`, so sampling follows whatever your
Ollama server defaults to. Nothing on this page measures how far repeated runs
move, so treat repeated scores as unpinned: this page does not show them to be
identical, and does not show them to differ. The `reproducibility_note` emitted
by `src/hermes_rubric/receipt.py` does not settle it either: it records the inputs,
backend and rubric hash, notes that Stage-1 rubric synthesis — bypassed here —
is not deterministic, and warns that a changed `rubric_hash` means the measuring
stick itself moved, so scores from runs with different hashes are not directly
comparable.

The command exits `0` and writes `"$workdir/result.json"`. Exit `0` means the
pipeline completed and produced that output — it says nothing about the scores,
and a low aggregate still exits `0`. A nonzero exit is a failure to assess, not
a verdict: `src/hermes_rubric/cli.py` exits `1` for a backend or input error,
`2` for Stage 1, `3` for Stage 2 and `4` for Stage 3. Exit `2` is shared —
argparse also uses it for a CLI usage error, such as a missing `--target` or
`--pin-rubric` together with `--artifact-class`. A usage error fails before any
stage runs and prints `usage:`; a Stage-1 failure prints `ERROR in Stage 1`.

## Read the result

```bash
WORKDIR="$workdir" python3 - <<'EOF'
import json
import os

with open(os.path.join(os.environ["WORKDIR"], "result.json")) as fh:
    result = json.load(fh)

print("schema_version:", result["schema_version"])
print("aggregate:", result["aggregate"], "/", result["max_possible"])
print("coverage:", result["coverage"]["status"], result["coverage"]["limitations"])
print("backend:", result["receipt"]["backend"])
print("rubric hash:", result["receipt"]["pipeline"]["stage_1_rubric_hash_sha256"][:16])

for dim in result["per_dim_scores"]:
    print(f"  {dim['dim_id']}: {dim['score']}")

for evidence in result["evidence_citations"]:
    for citation in evidence["citations"]:
        print(f"  {evidence['dim_id']} <- {citation['location']}: {citation['quote'][:60]}")
EOF
```

What to assert in your own harness — these hold for any backend:

- `schema_version` is present, and `per_dim_scores` has one entry per rubric
  dimension;
- every scored dimension has a matching entry in `evidence_citations`, and both
  clamps hold independently — a dimension with `evidence_found: false` scores at
  most `3`, and a dimension with `hedge: true` is clamped into `[3, 7]`, so a
  dimension that is both lands on `3`. Both are enforced in `_apply_clamps()` in
  `src/hermes_rubric/score.py` and asserted in `tests/test_quickstart_recipe.py`;
- `coverage.status` is `complete` only when the whole target was visible;
  `partial` means some of it was never inspected;
- `receipt` records `tool_version`, `backend`, the input hashes, and
  `stage_1_rubric_hash_sha256`.

Do not assert a particular aggregate or per-dimension score. A score is model
output measured against the rubric, not a truth claim about the target, and
nothing pins it for you: backends do not share decoding settings —
`_call_openai()` sends `temperature: 0` and `seed: 42` while `_call_ollama()`
sends neither, both in `src/hermes_rubric/backends.py` — so a score is not a
stable value to assert against.

## Assess in memory

```python
from hermes_rubric import FeedbackPolicy, assess

answer = "The agent output to assess"
task = "Material claims need checkable evidence."

result = assess(
    answer,
    intent="Evaluate accuracy and evidence grounding.",
    context=task,
    target_type="agent-output",
    backend="ollama-local",  # explicit; swap for a backend you have
)

print(f"aggregate: {result.aggregate}/10")
print(f"coverage: {result.coverage.status}")
print(result.feedback(FeedbackPolicy(minimum_score=7)).to_prompt())
```

Inspect citations and coverage before acting on the aggregate:

```python
for evidence in result.evidence_citations:
    print(evidence["dim_name"], evidence["citations"])

for limitation in result.coverage.limitations:
    print("coverage:", limitation)
```

## Read the result correctly

- Start with `coverage`. `partial` means some relevant material may be uninspected.
- Inspect `evidence_citations` and hedged dimensions.
- Use `per_dim_scores` and rationales before the aggregate.
- Treat the aggregate as signal, not verdict.
- Apply an explicit `FeedbackPolicy` only when your application owns a threshold.

Next: [Python API](API.md), [CLI](CLI.md), [Backends](BACKENDS.md), and [adapter contract](ADAPTERS.md).
