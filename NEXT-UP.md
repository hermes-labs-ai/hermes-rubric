# hermes-rubric — NEXT-UP tickets

> What this is: cold-pickup ticket queue for the open gaps (G2-G6, G9, G10) in
> `FLAGSHIP-SPEC.md`. G1, G7, G8 shipped 2026-04-24. Each ticket below is
> self-contained: a co-founder reopening this in two weeks should be able to
> pick any open ticket and start with the "Cheapest first move" command.

## Status table

| ID  | Gap                                                | Effort   | Status |
|-----|----------------------------------------------------|----------|--------|
| G1  | Cohen's κ across backends                          | 2-3d     | done   |
| G2  | Rubric registry: versioned, signed, reusable       | 1wk      | open   |
| G3  | Web UI: target+intent → rubric+evidence+score      | 2wk      | open   |
| G4  | Audit export: signed PDF + JSON bundle             | 1wk      | open   |
| G5  | API server `hermes-rubric serve`                   | 1wk      | open   |
| G6  | EU AI Act / ISO 42001 clause-mapping               | 3-5d     | open   |
| G7  | Native `--scope-class` + `--intent-debias` flags   | 1-2d     | done   |
| G8  | `--target-window-bytes` flag + warning             | 0.5d     | done   |
| G9  | Cross-backend reliability study, published         | 2wk+$50  | open   |
| G10 | 1-2 design-partner pilots                          | 4-8wk    | open   |

## Already-shipped (this week)

- **G1** — Cohen's κ metric implemented and exercised against the pre-registered
  ≥0.6 floor in FLAGSHIP-SPEC §"Pre-registered falsification."
- **G7** — `--scope-class` and `--intent-debias` are now native CLI flags
  (no longer wrapper-only via `~/bin/hermes-rubric-blinded`).
- **G8** — `--target-window-bytes` flag with size warning emitted when target
  exceeds the configured byte ceiling.

`main` is 18 commits ahead of `origin/main` and not yet pushed. 76 tests green.
`batch-mode` branch merged. Push deferred to 2026-04-25.

---

## G2 — Rubric registry: versioned, signed, reusable

- **Status:** open
- **Effort:** 1 week
- **Definition of done:** a `rubrics/` directory in-repo with at least 3
  versioned rubric YAMLs (e.g. `paper-methods-v1.yaml`, `pr-quality-v1.yaml`,
  `lead-fit-v1.yaml`), each with a `sha256` + Hermes Seal signature; CLI flag
  `--rubric <id>@<version>` that loads from the registry instead of synthesizing;
  `tests/test_rubric_registry.py` proves load + signature-verify + score against
  one fixture target per registered rubric.
- **Dependencies:** none. (G4 audit export will later cite registry IDs in
  receipts; build that order.)
- **Cheapest first move:** create `rubrics/` and write `rubrics/SCHEMA.md`
  defining the YAML fields (`id`, `version`, `dims[]`, `scope_class`,
  `synthesized_from`, `sha256`, `signature`). One file, no code yet.
- **Not in this ticket:** rubric authoring UI, registry distribution
  (publishing to PyPI / a hosted index), or rubric-merge logic across versions.
- **Cross-refs:** FLAGSHIP-SPEC §"v1.0 non-goals" ("closed-source rubrics" is
  excluded — this ticket is the open-registry counterpart). Reuse
  `hermes-seal` for signatures (`/Users/rbr_lpci/Documents/projects/hermes-seal/`).

---

## G3 — Web UI: target + intent → rubric + evidence + score

- **Status:** open
- **Effort:** 2 weeks
- **Definition of done:** a minimal web UI (single-page, served by G5's API
  server) that accepts `intent` text, `target` upload, `target-type` dropdown,
  `backend` dropdown; runs the pipeline; renders the JSON output as a
  human-readable card (rubric, per-dim scores w/ evidence pop-outs, hedge flags,
  receipt). Smoke test via Playwright: upload fixture, assert score card renders.
- **Dependencies:** G5 (API server) must land first — UI is a thin client over it.
- **Cheapest first move:** sketch the card layout as static HTML in
  `webui/mockup.html` against a captured JSON output from a prior run.
  No framework yet, no server yet.
- **Not in this ticket:** authentication, multi-user state, history view, or
  any rubric-editing UI (rubric authoring is out-of-scope until post-v1).
- **Cross-refs:** FLAGSHIP-SPEC §"Roadmap P4." Consider Next.js (matches
  `hermes-labs-v2/` stack at `~/Documents/Claude Code/hermes-labs-v2/`) for
  consistency, but a Flask/FastAPI + vanilla JS page is fine for v1.

---

## G4 — Audit export: signed PDF + JSON bundle

- **Status:** open
- **Effort:** 1 week
- **Definition of done:** `hermes-rubric export <run-id> --format pdf` and
  `--format bundle` commands. PDF contains rubric, per-dim scores w/ evidence
  citations, hedge flags, receipt block. Bundle is a tar.gz with the JSON
  output + prompt + raw evidence + Hermes Seal manifest. `tests/test_export.py`
  proves PDF renders without error and bundle verifies via `hermes-seal verify`.
- **Dependencies:** none for JSON bundle; PDF can use `weasyprint` or `reportlab`.
- **Cheapest first move:** add `hermes_rubric/export.py` with a
  `bundle(run_dir, out_path)` function that tars the existing per-run artifacts
  (no PDF yet). One function, one test.
- **Not in this ticket:** customer-branded PDF templates, multi-run roll-ups,
  redaction tooling, or per-customer signing keys.
- **Cross-refs:** FLAGSHIP-SPEC §"Auditability readiness" calls G4
  load-bearing for buyer scrutiny. Reuse `hermes-bundle` patterns
  (`~/Documents/projects/hermes-bundle/`) — it already produces sealed
  audit-evidence bundles for EU AI Act + ISO 42001.

---

## G5 — API server `hermes-rubric serve`

- **Status:** open
- **Effort:** 1 week
- **Definition of done:** `hermes-rubric serve --port 8788` starts a FastAPI
  server with `POST /score` (multipart: intent, target file, target-type,
  backend) returning the same JSON contract as the CLI. `tests/test_serve.py`
  uses TestClient to assert one round-trip on a fixture target. Receipt
  includes server-version + git SHA.
- **Dependencies:** none. G3 (web UI) consumes this.
- **Cheapest first move:** add `hermes_rubric/serve.py` with a single
  `/healthz` endpoint that returns `{"status":"ok","version":__version__}`.
  Registers no scoring logic yet — proves the wiring.
- **Not in this ticket:** auth, rate-limiting, multi-tenant isolation, async
  job queues. v1 is synchronous request/response.
- **Cross-refs:** FLAGSHIP-SPEC §"Roadmap P4." Reuse the CLI's
  argument parser by extracting shared validation into
  `hermes_rubric/inputs.py` (refactor before serve.py).

---

## G6 — EU AI Act / ISO 42001 clause-mapping

- **Status:** open
- **Effort:** 3-5 days
- **Definition of done:** `compliance/eu-ai-act-mapping.yaml` and
  `compliance/iso-42001-mapping.yaml` mapping each rubric dimension class
  (`evidence-gate`, `hedge-on-thin`, `receipt`, `cross-backend-κ`) to the
  specific clauses they discharge (Art. 14, Annex III, ISO 42001 §8.7, etc).
  `hermes-rubric --compliance eu-ai-act` adds a `compliance_coverage` block to
  the JSON output. `tests/test_compliance.py` asserts the mapping loads, every
  cited clause is reachable in the source standards index, and the coverage
  block is well-formed.
- **Dependencies:** none. G4 export will surface this in PDFs once both ship.
- **Cheapest first move:** create `compliance/SOURCES.md` listing the exact
  clauses (with text snippets) that the mapping will reference. Pulls the
  citation discipline forward before any code.
- **Not in this ticket:** SOC 2, NIST AI RMF, HIPAA, or sector-specific
  mappings. NIH/medical mapping is a v1.1 candidate.
- **Cross-refs:** FLAGSHIP-SPEC §"Auditability readiness" calls G6
  load-bearing for funder scrutiny. Reuse `hermes-bundle`'s
  `compliance/` index where it already overlaps.

---

## G9 — Cross-backend reliability study, published

- **Status:** open
- **Effort:** 2 weeks + ~$50 experiment cost
- **Definition of done:** an arXiv-ready preprint draft + reproducibility
  artifact in `studies/cross-backend-reliability/` containing: scoring runs
  across ≥4 backends (Haiku, Opus, qwen-plus, qwen-max) on the 4-paper applied
  corpus + an adversarial pair, per-pair Cohen's κ, the
  `evidence-stage-removed` ablation arm, and pass/fail against the
  pre-registered falsification conditions. Result published or rejected per
  those conditions — no fudging.
- **Dependencies:** G1 (κ metric) — done. Calibration set is already in repo.
- **Cheapest first move:** write `studies/cross-backend-reliability/PLAN.md`
  pre-registering exact run matrix, seeds, ablation arm, and the three numeric
  kill conditions copied verbatim from FLAGSHIP-SPEC.
- **Not in this ticket:** journal submission, peer review, or coverage
  beyond English text targets. Cross-language reliability is post-v1.
- **Cross-refs:** FLAGSHIP-SPEC §"Pre-registered falsification" — kill
  conditions are binding. `feedback_ci_green_not_accuracy.md` applies:
  fixture-valued assertions required, null result must be reportable.

---

## G10 — 1-2 design-partner pilots

- **Status:** open (gated on outreach, not engineering)
- **Effort:** 4-8 weeks (calendar; sales cycle)
- **Definition of done:** at least one signed pilot agreement with a design
  partner (regulated AI buyer or AI-product team) using hermes-rubric on real
  targets, with a written case study (≥2 pages) and a public quote in the
  v1.0 launch post. Stretch: 2 pilots, 1 medical + 1 enterprise.
- **Dependencies:** G4 (audit export) and G6 (compliance mapping) make the
  pitch concrete; G9 (reliability study) makes it defensible. Pilots can
  technically begin earlier on a "we'll add export when you need it" basis.
- **Cheapest first move:** add a `pilot-targets` row group to the GTM
  registry at `~/Desktop/MASTER-THREAD-REGISTRY.md` and tag the 5 most-promising
  existing 25-target accounts as "rubric pilot candidate." Outreach uses the
  existing 6-slot draft pipeline; no new infrastructure needed.
- **Not in this ticket:** paid engagements (pilots are free-with-case-study),
  multi-pilot coordination tooling, or a customer success function.
- **Cross-refs:** FLAGSHIP-SPEC §"Roadmap P5 (parallel)." Reuse Hermes Labs
  GTM corpus at `~/Desktop/hermes-labs-gtm-research/` and the
  `draft-target` skill for individualized outreach. `feedback_email_factorytalk_template.md`
  governs voice.

---

## Suggested execution order

Ordered by (a) dependency unlock, (b) effort-to-impact, (c) FLAGSHIP-SPEC
ship-criteria load-bearing weight.

1. **G6** (3-5d) — fast, unlocks regulatory-defensible language for G10
   outreach and G4 PDFs. Buyer-scrutiny load-bearing.
2. **G4** (1wk) — buyer-scrutiny load-bearing, no upstream deps. Pairs
   naturally with G6 mappings in the exported PDF.
3. **G2** (1wk) — registry stabilizes the receipt format that G4 cites.
   Independent of G3/G5, ship in parallel with G4 if bandwidth allows.
4. **G5** (1wk) — required prerequisite for G3. Synchronous v1.
5. **G9** (2wk + $50) — methodology defense; can run in background while
   G2/G4/G5 ship since experiments don't block engineering.
6. **G3** (2wk) — last engineering item; needs G5 in place.
7. **G10** (4-8wk calendar, parallel from week 1) — outreach starts as soon
   as G6 is in hand; pilots close as later Gs ship.

This sequence matches FLAGSHIP-SPEC's P1-P6 roadmap with G6 + G4 pulled
forward of G3 because they unlock both buyer scrutiny (G4) and funder
scrutiny (G6) — the two highest-leverage Series-A axes.
