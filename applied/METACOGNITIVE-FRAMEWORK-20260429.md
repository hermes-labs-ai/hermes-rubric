# Metacognitive Verification Framework — 2026-04-29

**Source:** Rolando Bosch directive, 2026-04-29 10:13 PT.
**Binding on:** Mission B (paper hardening), Mission C (Hermes-native rebuild pilot), HAL coordinator.
**Status:** SEALED before mission spawn. Verbatim copy of the 5 constraints below.

---

## 1. Forced Self-Verification (the Red-Team Scratchpad)

Before any file commit or final metric assertion in either mission, the subagent must output a brief `<verification_scratchpad>` block. In this block, the agent must:

- Play its own adversarial skeptic.
- Identify one likely edge case or failure mode of the code/text it is about to commit.
- Explain explicitly why the current approach survives that failure mode.

Only after this scratchpad resolves cleanly can the commit proceed.

If the scratchpad surfaces a failure mode the approach does NOT survive, the agent halts, logs the unresolved scratchpad, and escalates to coordinator before any commit.

---

## 2. Bulletproofing Mission C — the Embedding & Math Justification

If Mission C relies on Hungarian-matched cosine on dimension-description embeddings, it cannot treat the embeddings as a black box. In its methodology documentation and verification steps, Mission C must:

- **Rationalize the model:** explicitly justify which embedding model is used and why it is philosophically appropriate for this semantic space (rubric-dimension descriptions are short prose; the embedding must capture semantic equivalence at that granularity).
- **Validate the null distribution:** write out the mathematical logic for the random-permutation null. Prove (in writing) that the threshold derived actually separates genuine semantic equivalence from the model's baseline vocabulary bias.
- **Sanity check:** if the null distribution yields a threshold that looks artificially low or suspiciously perfect, the agent must flag it and halt C. We do not trade LLM-judge bias for embedding-space bias.

---

## 3. Bulletproofing Mission B — the Phantom Limb Check

Mission B is not just mechanically deleting lines. Cutting §6 and §7 risks leaving semantic phantom limbs. The Mission B subagent must:

- Read the paragraphs immediately preceding and following the cuts to ensure transition logic remains sound.
- Verify that no remaining claims in the introduction or abstract secretly rely on the amputated meta-tool experiment.
- Confirm that the 5 newly added citations actually support the specific sentences they are attached to, verifying against the scraped abstract snippets.

---

## 4. The I/O Quarantine (Coordinator Guardrail)

Mission B and Mission C must operate on strictly divergent, isolated directories:
- Mission B → `applied/mission-B-20260429/` for receipts; paper edits in `~/Documents/projects/hermes-content/papers/meta-rubric/`
- Mission C → `applied/mission-C-20260429/` for all artifacts; meta-tool wrapper code edits in `~/Documents/projects/hermes-rubric/meta_tool/`

Do NOT attempt to hot-swap or merge live. If C succeeds, Roli oversees integration.

---

## 5. Execution

Pre-register the docs. Hermetically seal them locally. Spawn the Opus subagents staggered by 2 minutes. Execute without hedging. Report back only when Phase 1 of C is complete, or if a critical halt-trigger (or scratchpad failure) is tripped. Roli is watching the logs.

---

## Coordinator (HAL) responsibilities under this framework

- HAL does not commit on behalf of subagents; subagents commit themselves with their own scratchpads.
- HAL does not merge B and C output until Roli authorizes.
- HAL does not generate scratchpads on behalf of subagents; if a subagent halts on scratchpad failure, HAL surfaces it.
- HAL does not issue status updates between framework-defined surfacing events except to flag a critical halt.
