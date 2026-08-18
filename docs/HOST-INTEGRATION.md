# Host integration contract

A host — a coding-agent harness, a release script, a CI wrapper — may offer to run Hermes Rubric immediately before a consequential, difficult-to-reverse action such as a public merge or release. The offer is optional by default: there is no automatic organization-wide gate, and nothing in this package intercepts an action. This page defines the small contract a host follows so the offer, the remembered answer, and the resulting evidence stay honest.

## Binding a run to the action

A Rubric run is only meaningful for the exact thing about to happen. Before calling `assess()`, the host resolves the pending action into an immutable binding:

```text
RubricRunBinding:
  target:    the exact artifact at stake (e.g., the merge diff or release archive)
  intent:    why this boundary is being assessed
  context:   action kind, repository, exact base and head revisions, and any policy context
  revision:  immutable identifiers — commit SHAs, release tag, or content digest
```

For a merge boundary, "revision" means **both** sides: the host resolves the mutable refs (`base_ref`, the PR branch) to an exact base commit SHA and an exact head commit SHA *before* `assess()`, and builds the target diff and the context string from those SHAs — never from a ref that can move underneath the run. `target`, `intent`, and `context` are passed to `assess()` as-is; the resolved SHAs belong in `context` so they appear in the receipt's input hashes.

If either revision changes between scoring and acting — a new push to the branch, a commit landing on the base, a rebuilt artifact — the evidence no longer describes the pending action. The host must re-offer at the new revisions rather than reuse the stale result, and a check made *before* the action step is advisory only: the authoritative comparison is the atomic compare-and-act inside the decision step itself (see `host_decides` below).

## The six explicit choices

This six-answer contract and its scope semantics are specified in [issue #8](https://github.com/hermes-labs-ai/hermes-rubric/issues/8). When a configured action is detected and no remembered choice applies, the host asks one question with exactly six answers — a decision (yes/no) crossed with a scope:

| Choice | Effect | Remembered |
| --- | --- | --- |
| yes, this action | run Rubric now, once | never stored |
| yes, for this session | run Rubric at this boundary without re-asking, until the session ends | session store |
| yes, for this harness | run Rubric at this boundary without re-asking, until reset | harness store |
| no, this action | skip Rubric now, once | never stored |
| no, for this session | do not offer again this session | session store |
| no, for this harness | do not offer again for this harness, until reset | harness store |

Scope semantics: an *action* answer applies to the single pending action and is never persisted; a *session* answer lasts for the current host session and is cleared when it ends; a *harness* answer persists for this host installation until explicitly reset. When both a session and a harness answer exist, the host applies the narrower (session) one. In every case the answer governs only whether the scorer runs — never whether the action proceeds.

A remembered choice is host state, and the host must keep it explicit, inspectable, and resettable:

```text
ConsentRecord:
  decision:    "yes" | "no"
  scope:       "session" | "harness"
  action_kind: e.g. "github.pr_merge", "github.release"
  recorded_at: timestamp
```

**When a choice may be stored.** The host must distinguish a *recalled* choice (found in the session or harness store) from a *newly prompted* one, because they have different persistence rules:

- A recalled choice is applied but never rewritten: recall does not re-store the record, refresh `recorded_at`, or change its scope.
- A newly prompted **yes** with session or harness scope is persisted only after the assessment completes successfully for the still-current binding — never before `assess()` returns, and never if the revisions moved while scoring.
- A newly prompted **no** with session or harness scope involves no assessment; its scoped skip is recorded only as part of the successful host decision path — after `host_decides` completes — not before the host decision step runs.
- Action-scoped answers are never stored, and a failed or stale run must not create, consume, or alter any `ConsentRecord` (see [Failure behavior](#failure-behavior)).

## Ownership boundary

The host owns:

- detecting that a configured irreversible action is about to run;
- the selectable UI for the six choices;
- persisting, listing, and resetting `ConsentRecord`s at their declared scope;
- deciding, after seeing the evidence (or a failure), whether the action proceeds.

Hermes Rubric owns nothing beyond the assessment transaction. It remains a stateless artifact scorer: it does not store consent, does not detect or intercept GitHub operations, does not merge or release, and its result is evidence for human or host judgment — never authorization. A high aggregate after a "yes" is still not permission to act, and the aggregate is a signal, not a verdict.

## Failure behavior

If no backend is available (backend auto-detection raises `RuntimeError`) or any stage fails (`AssessmentError` with its `stage`), control returns to the host with the failure surfaced. The pending action is left exactly as it was:

- the target is not mutated and the action is neither performed nor cancelled by Hermes;
- the failure is not translated into a passing or failing score, nor into silent approval;
- consent state is untouched: no existing `ConsentRecord` is consumed, refreshed, or flipped, and no new one is created — a session- or harness-scoped answer prompted just before the failed run is discarded, not stored;
- whether to proceed without evidence, retry, or wait is host policy (fail-open or fail-closed), stated to the user rather than assumed.

## Example: public GitHub merge boundary

A harness is about to merge PR #42 — a synthetic example, not a real pull request — into `main` of a public repository. Pseudocode for the boundary:

```python
from hermes_rubric import AssessmentError, assess

def before_pr_merge(pr, session, harness):
    remembered = session.recall("github.pr_merge") or harness.recall("github.pr_merge")
    choice = remembered or prompt_six_choices("Run Hermes Rubric before merging?")
    newly_prompted = remembered is None
    # Nothing is stored yet: a recalled choice is never rewritten, and a
    # newly prompted one is persisted only at the success points below.

    # Immutable binding: resolve both mutable refs to exact commit SHAs
    # before assess(); target and context are built from these SHAs only.
    base_sha = pr.resolve_base_sha()
    head_sha = pr.resolve_head_sha()

    if choice.decision == "no":
        # No assessment on "no". The scoped skip is recorded only as part
        # of the successful host decision path, never before host_decides.
        outcome = host_decides(pr, evidence=None,
                               expected_base_sha=base_sha,
                               expected_head_sha=head_sha)
        if outcome.completed and newly_prompted and choice.scope != "action":
            (session if choice.scope == "session" else harness).remember(choice)
        return outcome

    try:
        result = assess(
            target=pr.diff_between(base_sha, head_sha),
            intent="Assess whether this change is safe to merge to main.",
            context=f"action=github.pr_merge repo={pr.repo} pr={pr.number} "
                    f"base={base_sha} head={head_sha}",
        )
    except (AssessmentError, RuntimeError) as error:
        # Failed run: no ConsentRecord is created, consumed, or altered.
        return host_decides(pr, evidence=None, failure=error,
                            expected_base_sha=base_sha,
                            expected_head_sha=head_sha)

    if pr.resolve_head_sha() != head_sha or pr.resolve_base_sha() != base_sha:
        # Advisory early check: a revision moved while scoring, so the
        # evidence is stale. Nothing was stored — re-offer at the new SHAs.
        return before_pr_merge(pr, session, harness)

    # Assessment succeeded for the still-current binding: only now may a
    # newly prompted session/harness "yes" be persisted.
    if newly_prompted and choice.scope != "action":
        (session if choice.scope == "session" else harness).remember(choice)

    return host_decides(pr, evidence=result.to_dict(),
                        expected_base_sha=base_sha,
                        expected_head_sha=head_sha)
```

`host_decides` is the host's own judgment step on every path: it shows the cited evidence, coverage, and receipt (or the failure) and performs or declines the merge itself. It receives `expected_base_sha` and `expected_head_sha`, and when it does act it must perform the merge as an **atomic compare-and-act**: the merge is executed conditioned on the base and head still matching the expected SHAs at action time (for example, a merge API parameter that rejects the call if the head has moved), and if either differs, `host_decides` refuses to act and re-offers at the new revisions. The staleness check before `host_decides` in the pseudocode is an advisory fast path only — a race can still land between that check and the action, so the compare inside the decision step is the authoritative one. The score and evidence never authorize the action on any path. The same shape applies at a release boundary with `action_kind="github.release"`, `target` as the release artifact, and the expected revision as the tag or artifact digest.

## Out of scope

This contract deliberately excludes: a bundled host UI, consent storage inside Hermes Rubric, making Rubric mandatory for pushes or pull requests, and performing any irreversible action after scoring.
