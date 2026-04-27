# Section 11 Citation Verification Log

Every citation included in PAPER-v1.md Section 11 was fetched live from arxiv.org on 2026-04-24 and verified for title / author / year / abstract alignment with the claim made.

---

## [1] Zheng et al. 2023 — MT-Bench / LLM-as-a-Judge
- **arXiv:** 2306.05685
- **URL:** https://arxiv.org/abs/2306.05685
- **Title:** Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena
- **Authors:** Lianmin Zheng, Wei-Lin Chiang, Ying Sheng, Siyuan Zhuang, Zhanghao Wu, Yonghao Zhuang, Zi Lin, Zhuohan Li, Dacheng Li, Eric P. Xing, Hao Zhang, Joseph E. Gonzalez, Ion Stoica
- **Posted:** 2023-06-09
- **Claim used:** Establishes LLM-as-judge framework + identifies position, verbosity, and self-enhancement biases.
- **Abstract excerpt:** "We examine the usage and limitations of LLM-as-a-judge, including position, verbosity, and self-enhancement biases ... strong LLM judges like GPT-4 can match both controlled and crowdsourced human preferences well, achieving over 80% agreement."

## [2] Liu et al. 2023 — G-Eval
- **arXiv:** 2303.16634
- **URL:** https://arxiv.org/abs/2303.16634
- **Title:** G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment
- **Authors:** Yang Liu, Dan Iter, Yichong Xu, Shuohang Wang, Ruochen Xu, Chenguang Zhu
- **Posted:** 2023-03-29
- **Claim used:** Form-filling paradigm — single-prompt multi-aspect rubric with structured fields. Direct ancestor of our `<DIM>`-block batched mode.
- **Abstract excerpt:** "G-Eval, a framework of using large language models with chain-of-thoughts (CoT) and a form-filling paradigm, to assess the quality of NLG outputs."

## [3] Shankar et al. 2024 — Who Validates the Validators
- **arXiv:** 2404.12272
- **URL:** https://arxiv.org/abs/2404.12272
- **Title:** Who Validates the Validators? Aligning LLM-Assisted Evaluation of LLM Outputs with Human Preferences
- **Authors:** Shreya Shankar, J.D. Zamfirescu-Pereira, Björn Hartmann, Aditya G. Parameswaran, Ian Arawjo
- **Posted:** 2024-04-18
- **Claim used:** "Criteria drift" finding — evaluation criteria are not independent of observed outputs. Motivates the need to measure refactor-equivalence rather than assume it.
- **Abstract excerpt:** "we identify a phenomenon we dub criteria drift: users need criteria to grade outputs, but grading outputs helps users define criteria ... raising serious questions for approaches that assume the independence of evaluation from observation of model outputs."

## [4] Lee et al. 2024 — Evaluating the Consistency of LLM Evaluators
- **arXiv:** 2412.00543
- **URL:** https://arxiv.org/abs/2412.00543
- **Title:** Evaluating the Consistency of LLM Evaluators
- **Authors:** Noah Lee, Jiwoo Hong, James Thorne
- **Posted:** 2024-11-30
- **Claim used:** Self-Consistency vs Inter-scale Consistency. Most adjacent prior work to our prompt-shape consistency axis.
- **Abstract excerpt:** "two aspects of consistency in LLM evaluations, Self-Consistency (SC) and Inter-scale Consistency (IC), on different scoring scales and criterion granularity ... strong proprietary models are not necessarily consistent evaluators."

## [5] Errica et al. 2024 — Sensitivity and Consistency to Prompt Engineering
- **arXiv:** 2406.12334
- **URL:** https://arxiv.org/abs/2406.12334
- **Title:** What Did I Do Wrong? Quantifying LLMs' Sensitivity and Consistency to Prompt Engineering
- **Authors:** Federico Errica, Giuseppe Siracusano, Davide Sanvito, Roberto Bifulco
- **Posted:** 2024-06-18
- **Claim used:** Defines sensitivity (pred changes across paraphrases) and consistency (pred variance within class) as ground-truth-free reliability metrics. Frames our σ_Δ=0 cells as "consistent shifts under sensitivity-inducing prompt rewording."
- **Abstract excerpt:** "sensitivity measures changes of predictions across rephrasings of the prompt, and does not require access to ground truth labels ... consistency measures how predictions vary across rephrasings for elements of the same class."

## [6] Guan et al. 2025 — The Order Effect
- **arXiv:** 2502.04134
- **URL:** https://arxiv.org/abs/2502.04134
- **Title:** The Order Effect: Investigating Prompt Sensitivity to Input Order in LLMs
- **Authors:** Bryan Guan, Tanya Roosta, Peyman Passban, Mehdi Rezagholizadeh
- **Posted:** 2025-02-06
- **Claim used:** Shows input-order sensitivity in closed-source LLMs across paraphrasing, relevance judgment, MCQ. Adjacent failure mode to ours; we observe shifts under prompt-shape variation rather than item-order variation.
- **Abstract excerpt:** "input order significantly affects performance across tasks, with shuffled inputs leading to measurable declines in output accuracy."

## [7] Yu et al. 2025 — DeCE / Decomposed Criteria-Based Evaluation
- **arXiv:** 2509.16093
- **URL:** https://arxiv.org/abs/2509.16093
- **Title:** Beyond Pointwise Scores: Decomposed Criteria-Based Evaluation of LLM Responses
- **Authors:** Fangyi Yu, Nabeel Seedat, Dasha Herrmannova, Frank Schilder, Jonathan Richard Schwarz
- **Posted:** 2025-09-19
- **Claim used:** Decomposed multi-criteria evaluation outperforms pointwise scoring (r=0.78 vs r=0.35) on legal QA. Strongly motivates the multi-aspect rubric design but does not measure batched-vs-per-criterion equivalence — that gap is what we fill.
- **Abstract excerpt:** "DeCE achieves substantially stronger correlation with expert judgments (r=0.78), compared to traditional metrics (r=0.12), pointwise LLM scoring (r=0.35), and modern multidimensional evaluators (r=0.48)."

## [8] Zhang et al. 2025 — Through the Judge's Eyes
- **arXiv:** 2510.25860
- **URL:** https://arxiv.org/abs/2510.25860
- **Title:** Through the Judge's Eyes: Inferred Thinking Traces Improve Reliability of LLM Raters
- **Authors:** Xingjian Zhang, Tianhong Gao, Suliang Jin, Tianhao Wang, Teng Ye, Eytan Adar, Qiaozhu Mei
- **Posted:** 2025-10-29
- **Claim used:** Recent (post-cutoff for many models) work showing reliability of LLM raters can be improved via inferred thinking traces, and that refined annotation guidelines improve cross-model agreement. Frames reliability as a property of the prompt-shape, consistent with our σ_Δ=0 finding.
- **Abstract excerpt:** "the refined annotation guidelines increase agreement among different LLM models. These results suggest that LLMs can serve as practical proxies for otherwise unrevealed human thinking traces."

## [9] Choi et al. 2026 — IRT Diagnosis of LLM Judges
- **arXiv:** 2602.00521
- **URL:** https://arxiv.org/abs/2602.00521
- **Title:** Diagnosing the Reliability of LLM-as-a-Judge via Item Response Theory
- **Authors:** Junhyuk Choi, Sohhyung Park, Chanhee Cho, Hyeonchu Park, Bugeun Kim
- **Posted:** 2026-01-31
- **Claim used:** Most recent and most directly aligned reliability framework: defines intrinsic consistency as "stability of measurement behavior under prompt variations." Our work is one empirical instance of measuring exactly that, on a specific prompt-shape axis (batched vs per-dim).
- **Abstract excerpt:** "intrinsic consistency, defined as the stability of measurement behavior under prompt variations, and (2) human alignment, capturing correspondence with human quality assessments."

## [10] Yeadon et al. 2026 — Criterion-referenceability
- **arXiv:** 2603.14732
- **URL:** https://arxiv.org/abs/2603.14732
- **Title:** Criterion-referenceability determines LLM-as-a-judge validity across physics assessment formats
- **Authors:** Will Yeadon, Tom Hardy, Paul Mackay, Elise Agra
- **Posted:** 2026-03-16
- **Claim used:** Explains target-conditional validity differences (essays vs structured exams vs code-based plots). Lines up cleanly with our T1/T4 result: high-evidence structured targets (T1) and report-style targets (T4) drive most of the per-dim shift; thin or empty targets (T2/T3/T5) show κ → 1.
- **Abstract excerpt:** "validity tracks 'criterion-referenceability—the extent to which a task maps to explicit, observable grading features—and benchmark reliability, rather than raw model capability.'"

---

## Candidates considered and dropped

- **2207.07051** — title not matched to a relevant claim in our scope; dropped to avoid padding.
- **2308.11483, 2309.03882, 2310.11324, 2311.12022, 2401.15884, 2403.14403, 2404.00610, 2407.10362, 2410.19803, 2411.10541, 2503.17332, 2504.11001, 2507.11473** — RAG / retrieval / red-teaming / benchmark papers surfaced by search but off-topic for batched-vs-per-dim rubric scoring.
- **2506.13023** ("A Practical Guide for Evaluating LLMs and LLM-Reliant Systems") — practitioner guide; survey-shaped, no specific empirical claim we'd cite as a peer result.
- **2009.03300, 2501.14249, 2406.06581, 2310.11511** — surfaced as MMLU / Self-RAG / benchmark references in unrelated contexts; not relevant.

## Threads with no usable result

- **Audit-evidence / EU-AI-Act thread** turned up only EU policy pages and practitioner blog posts; no peer-reviewed arxiv work that ties LLM-rubric grading to AI Act conformity assessment specifically. We acknowledge that gap honestly in Section 11 rather than fabricating coverage.

## [11] Landis and Koch 1977 — Inter-rater agreement bands (added 2026-04-26 for κ-threshold grounding)
- **DOI:** 10.2307/2529310
- **Journal:** Biometrics, 33(1), 159–174
- **Title:** The measurement of observer agreement for categorical data
- **Authors:** J. Richard Landis, Gary G. Koch
- **Claim used:** Canonical interpretation table for Cohen's κ on categorical data: 0.41-0.60 = "moderate," 0.61-0.80 = "substantial," 0.81-1.00 = "almost perfect." Used to justify the pre-registered κ ≥ 0.6 floor as the moderate/substantial boundary.
- **Verification:** Pre-arxiv reference (1977). Standard Biometrics citation; DOI resolves at https://doi.org/10.2307/2529310. Bibliographic record verified against the Biometrics journal record.
