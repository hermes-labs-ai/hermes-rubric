# Citation Verification Log — META-RUBRIC paper

Every citation in `paper.md` was either reused from the verified set in
`hermes-content/papers/batch-equivalence/RELATED-WORK-VERIFICATION.md` (paper 2)
or fetched live from arxiv on 2026-04-24 and verified against the abstract.

---

## Reused from paper 2's verification log (8)

The following citations were verified against fetched arxiv abstracts on
2026-04-24 during the `batch-equivalence` paper build. Their entries in
`paper.bib` are byte-identical with the paper-2 bib. Source log:
`/tmp/related-work-research/verification.md`.

- [1] Zheng et al. 2023 — `arXiv:2306.05685` — MT-Bench / LLM-as-a-Judge.
- [2] Liu et al. 2023 — `arXiv:2303.16634` — G-Eval form-filling paradigm.
- [3] Shankar et al. 2024 — `arXiv:2404.12272` — criteria drift.
- [4] Lee et al. 2024 — `arXiv:2412.00543` — Self-Consistency / Inter-scale Consistency.
- [5] Errica et al. 2024 — `arXiv:2406.12334` — sensitivity / consistency without ground truth.
- [6] Yu et al. 2025 — `arXiv:2509.16093` — DeCE decomposed criteria evaluation.
- [7] Choi et al. 2026 — `arXiv:2602.00521` — IRT diagnosis of LLM judges.
- [8] Yeadon et al. 2026 — `arXiv:2603.14732` — criterion-referenceability.

---

## Newly fetched and verified for this paper (4)

### [9] Zeng et al. 2023 — LLMBar
- **arXiv:** 2310.07641
- **URL:** https://arxiv.org/abs/2310.07641
- **Title:** Evaluating Large Language Models at Evaluating Instruction Following
- **Authors:** Zhiyuan Zeng, Jiatong Yu, Tianyu Gao, Yu Meng, Tanya Goyal, Danqi Chen
- **Posted:** 2023-10-11 (v1); 2024-04-16 (v2)
- **Claim used:** Meta-evaluation benchmark for LLM evaluators (419 curated output pairs with adversarial deceptive qualities). Establishes that meta-evaluation infrastructure exists but is benchmark-shaped, not framework-shaped — motivates our opinionated specification.
- **Abstract excerpt:** "LLMBar, a meta-evaluation benchmark featuring 419 manually curated output pairs where one follows instructions while the other deliberately violates them while possess[ing] deceptive qualities that mislead an LLM evaluator, e.g., a more engaging tone."

### [10] Chern et al. 2024 — ScaleEval
- **arXiv:** 2401.16788
- **URL:** https://arxiv.org/abs/2401.16788
- **Title:** Can Large Language Models be Trusted for Evaluation? Scalable Meta-Evaluation of LLMs as Evaluators via Agent Debate
- **Authors:** Steffi Chern, Ethan Chern, Graham Neubig, Pengfei Liu
- **Posted:** 2024-01-30
- **Claim used:** Agent-debate framework for scalable meta-evaluation of LLM evaluators. Adjacent prior work; we cite it to acknowledge that meta-evaluation primitives exist but do not yield a frozen specification.
- **Abstract excerpt:** "meta-evaluation conducted to assess the effectiveness of these LLMs as evaluators is typically constrained by the coverage of existing benchmarks or requires extensive human annotation ... ScaleEval, an agent-debate-assisted meta-evaluation framework that leverages the capabilities of multiple communicative LLM agents."

### [11] Rao and Callison-Burch 2026 — Autorubric
- **arXiv:** 2603.00077
- **URL:** https://arxiv.org/abs/2603.00077
- **Title:** Autorubric: Unifying Rubric-based LLM Evaluation
- **Authors:** Delip Rao, Chris Callison-Burch
- **Posted:** 2026-02-13 (v1); 2026-04-03 (v2)
- **Claim used:** Consolidates ensemble judging, bias mitigation, few-shot calibration into unified rubric infrastructure. Closest contemporary framework; we position the META-RUBRIC as a structural specification at the rubric layer rather than an evaluation infrastructure.
- **Abstract excerpt:** "consolidates 'ensemble judging, bias mitigation, few-shot calibration' and related methods into unified infrastructure ... features analytic rubrics supporting multiple criterion types, single and ensemble evaluation modes, calibration through few-shot examples, bias reduction strategies, and psychometric measurement tools."

### [12] Tang et al. 2026 — Reliable LLM-Assisted Rubric Scoring
- **arXiv:** 2604.12227
- **URL:** https://arxiv.org/abs/2604.12227
- **Title:** Designing Reliable LLM-Assisted Rubric Scoring for Constructed Responses: Evidence from Physics Exams
- **Authors:** Xiuxiu Tang, G. Alex Ambrose, Ying Cheng
- **Posted:** 2026-04-14
- **Claim used:** Empirical demonstration that structured checklist-based rubrics outperform holistic approaches for LLM-assisted scoring; analytic rubric reliability evidence from the educational measurement community.
- **Abstract excerpt:** "structured, checklist-based rubrics outperform holistic approaches, while prompting variations and temperature adjustments have minimal influence ... effective AI-assisted assessment in STEM requires well-designed rubrics emphasizing clearly defined skills."

---

## Companion artifact (1, non-arxiv)

- [13] `batchequiv2026` — Hermes Labs companion paper at `hermes-content/papers/batch-equivalence/`. Cited for the prompt-shape consistency finding referenced in §5. Not an arxiv preprint; cited as an internal companion artifact.

---

## Not cited (considered and dropped)

- **arxiv 2604.00259** (LLM Essay Scoring Under Holistic and Analytic Rubrics) — strong candidate but its central finding (holistic-analytic transfer) is adjacent rather than load-bearing for our argument; would have been padding.
- **arxiv 2503.23989** (Rubric Is All You Need: code evaluation) — relevant to question-specific rubrics but the META-RUBRIC's contribution is at the meta-layer, not rubric design per se.
- **arxiv 2410.17578** (MM-Eval multilingual) — language-coverage angle not load-bearing for our claim.
- **arxiv 2502.12052** (Dual-Perspective NLG Meta-Evaluation) — automatic benchmark construction is upstream of our concern; not cited to avoid scope drift.

These are documented for honest disclosure; the citation set is sized to support the specific claims in the paper, not to demonstrate reading volume.
