# CLI reference

Full flag and subcommand reference for hermes-rubric.

The CLI delegates successful runs to the same `assess_path()` transaction as
the Python API. Existing flags, stage exit codes, default stdout behavior, and
legacy JSON keys are preserved.

## Synopsis

```
hermes-rubric --target <path> [options]
hermes-rubric --version
hermes-rubric kappa --run1 <result_a.json> --run2 <result_b.json>
```

## Flags

| Flag | Default | Purpose |
|---|---|---|
| `--version` | n/a | Print the installed Hermes Rubric version and exit |
| `--target <path>` | required | File or directory to score |
| `--intent <text>` | required (unless `--artifact-class`) | One-sentence goal for the scoring run |
| `--context <path>` | required (unless `--artifact-class`) | Context file the rubric synthesizer uses |
| `--target-type <label>` | `document` | Tag for the target kind (e.g. `paper`, `tool`, `repo`) |
| `--out <path>` | stdout | Output JSON path |
| `--backend <name>` | auto-detect | One of: `claude-cli`, `ollama-local`, `dashscope-qwen`, `google-gemini`, `openai`, `openai-sdk`, `google-genai` |
| `--scope-class <name>` | none | `gate-plan` / `sweep-plan` / `results-bundle`. Biases the synthesizer toward the right axes |
| `--intent-debias` | off | Prepend a debias preamble that neutralizes valence-loaded framing in the intent |
| `--artifact-class <name>` | none | Use a deterministic class template instead of LLM synthesis (see [Class-aware mode](#class-aware-mode)) |
| `--batch` | off | Bundle evidence + scoring into one LLM call per stage; falls back to per-dim on parse failure |
| `--target-window-bytes <n>` | `8000` | Byte cap for target evidence content; oversize files emit a stderr warning |
| `--context-window-bytes <n>` | `8000` | Byte cap for Stage-1 synthesis context; independent of the target evidence window |
| `--verbose` | off | Print stage progress to stderr |

## Coverage in JSON output

Version 1.1 adds `schema_version` and `coverage` without removing or renaming
existing keys. The current evidence strategy is a UTF-8-safe target prefix.
When a target or directory exceeds the configured window/source limits,
`coverage.status` is `partial` and `coverage.limitations` explains what was not
inspected. Missing evidence under partial coverage is not proof of absence.

## Subcommands

### `kappa`

Computes Cohen's κ between two completed runs.

```
hermes-rubric kappa --run1 <result_a.json> --run2 <result_b.json>
```

See `hermes-rubric kappa --help` for full options.

## Class-aware mode

When you score the same kind of artifact repeatedly, Stage-1 LLM rubric synthesis re-invents the dim set on every run. Same target, three runs, three different rubric hashes. Class templates fix that:

```bash
hermes-rubric --artifact-class social-post --target post.md --out result.json
```

Each class is a YAML at `hermes_rubric/classes/<name>.yaml` defining a fixed dim set, weights, voice priors, and class-specific slop signatures. Same input + same class = same rubric across runs.

Bundled classes:
- `social-post`
- `show-hn-post`
- `linkedin-post`
- `outreach-email`
- `repo-readme`

To add your own: in a development checkout (`pip install -e .`), drop a YAML next to the bundled ones. For installed distributions, fork the repo or maintain class YAMLs in your own package and load them via `hermes_rubric.classes.load_class()`. See `src/hermes_rubric/classes/__init__.py` for the loader.

## Examples

### Score a paper

```bash
hermes-rubric \
  --intent "rate this as a publication-ready research artifact" \
  --context STYLE-GUIDE.md \
  --target paper.md \
  --out result.json
```

### Score a Show HN post deterministically

```bash
hermes-rubric --artifact-class show-hn-post --target post.md --out result.json
```

### Cross-backend agreement check

```bash
hermes-rubric --intent "rate publication readiness" --context STYLE-GUIDE.md --target paper.md --backend claude-cli --out a.json
hermes-rubric --intent "rate publication readiness" --context STYLE-GUIDE.md --target paper.md --backend ollama-local --out b.json
hermes-rubric kappa --run1 a.json --run2 b.json
```

### Debiased scoring of a high-stakes artifact

```bash
hermes-rubric \
  --intent "is this paper publication-ready" \
  --context CONTRIBUTING.md \
  --target paper.md \
  --intent-debias \
  --backend claude-cli \
  --out result.json
```

`--intent-debias` strips authorship and conventional priors from the intent. Use it when valence in the intent ("is this great paper") would bias the synthesized rubric.
