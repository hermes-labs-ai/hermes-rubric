# Quickstart

## Install

```bash
pip install hermes-rubric==1.2.1
hermes-rubric --version
```

The pin is the release this page was verified against; drop it to take the
latest. `--version` prints `hermes-rubric 1.2.1` and proves the install. It
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
cat > /tmp/post.md <<'EOF'
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
  --target /tmp/post.md \
  --backend ollama-local \
  --out /tmp/result.json \
  --verbose
```

`--artifact-class social-post` loads a bundled rubric instead of
synthesizing one — its nine dimensions are defined in
`src/hermes_rubric/classes/social-post.yaml` — so Stage 1 is skipped and the
dimension set and `stage_1_rubric_hash_sha256` are identical across runs. That
makes *rubric selection* deterministic. The scores themselves are model output
and are not: two runs of this exact command on the same file can differ.

The command exits `0` and writes `/tmp/result.json`. A nonzero exit is a
staged failure, not a low score: `src/hermes_rubric/cli.py` exits `1` for a
backend or input error, `2` for Stage 1, `3` for Stage 2 and `4` for Stage 3.

## Read the result

```bash
python3 - <<'EOF'
import json

result = json.load(open("/tmp/result.json"))

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

Do not assert a particular aggregate or per-dimension score. The same target
and the same rubric hash can score differently across backends and runs, and a
score is not a truth claim about the target.

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
