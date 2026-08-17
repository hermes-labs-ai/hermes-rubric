# Host integration contract

A host — a coding-agent harness, a release script, a CI wrapper — may offer to run Hermes Rubric immediately before a consequential, difficult-to-reverse action such as a public merge or release. The offer is optional by default: there is no automatic organization-wide gate, and nothing in this package intercepts an action. This page defines the small contract a host follows so the offer, the remembered answer, and the resulting evidence stay honest.

## Binding a run to the action

A Rubric run is only meaningful for the exact thing about to happen. Before calling `assess()`, the host resolves the pending action into an immutable binding:

```text
RubricRunBinding:
  target:    the exact artifact at stake (e.g., the merge diff or release archive)
  intent:    why this boundary is being assessed
  context:   action kind, repository, base/head, and any policy context
  revision:  immutable identifier — commit SHA, release tag, or content digest
```

`target`, `intent`, and `context` are passed to `assess()` as-is; `revision` belongs in `context` so it appears in the receipt's input hashes. If the revision changes between scoring and acting — a new push to the branch, a rebuilt artifact — the evidence no longer describes the pending action, and the host must re-offer at the new revision rather than reuse the stale result.

## The six explicit choices

When a configured action is detected and no remembered choice applies, the host asks one question with exactly six answers — a decision (yes/no) crossed with a scope:

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
- the remembered `ConsentRecord` is unchanged — a failed run does not consume or flip consent;
- whether to proceed without evidence, retry, or wait is host policy (fail-open or fail-closed), stated to the user rather than assumed.

## Example: public GitHub merge boundary

A harness is about to merge PR #42 into `main` of a public repository. Pseudocode for the boundary:

```python
from hermes_rubric import AssessmentError, assess

def before_pr_merge(pr, session, harness):
    choice = (
        session.recall("github.pr_merge")
        or harness.recall("github.pr_merge")
        or prompt_six_choices("Run Hermes Rubric before merging?")
    )
    if choice.scope != "action":
        (session if choice.scope == "session" else harness).remember(choice)
    if choice.decision == "no":
        return host_decides(pr, evidence=None)

    revision = pr.head_sha  # immutable binding
    try:
        result = assess(
            target=pr.diff_at(revision),
            intent="Assess whether this change is safe to merge to main.",
            context=f"action=github.pr_merge repo={pr.repo} pr={pr.number} "
                    f"base={pr.base_ref} head={revision}",
        )
    except (AssessmentError, RuntimeError) as error:
        return host_decides(pr, evidence=None, failure=error)

    if pr.head_sha != revision:
        # branch moved while scoring; evidence is stale — re-offer at the new head
        return before_pr_merge(pr, session, harness)
    return host_decides(pr, evidence=result.to_dict())
```

`host_decides` is the host's own judgment step on every path: it shows the cited evidence, coverage, and receipt (or the failure) and performs or declines the merge itself. The same shape applies at a release boundary with `action_kind="github.release"`, `target` as the release artifact, and `revision` as the tag or artifact digest.

## Out of scope

This contract deliberately excludes: a bundled host UI, consent storage inside Hermes Rubric, making Rubric mandatory for pushes or pull requests, and performing any irreversible action after scoring.
