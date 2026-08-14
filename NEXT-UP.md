# Next up after v1.1

Version 1.1 establishes the portable assessment boundary. The next correctness problem is evidence coverage beyond a single prefix.

## v1.2 evidence coverage engine

Target outcome: “no evidence” is distinguishable from “not inspected.”

Planned primitives:

- versioned evidence sources, chunks, and a coverage manifest;
- stable source IDs and line/section/byte locations;
- deterministic UTF-8 chunk planning;
- explicit bounded and full inspection modes;
- per-dimension chunk selection and citation merge/deduplication;
- contradictory-evidence capture;
- states for inspected, supported, contradicted, excluded, truncated, unavailable, and provider-failed material;
- caller-visible byte, chunk, call, and cost budgets;
- receipt telemetry for requested and effective modes.

The acceptance boundary is strict: excluded-by-budget material must never be reduced to `evidence_found=false` without a coverage gap.

Framework adapters follow after this core coverage contract is stable. They should remain optional extras and call public APIs only.
