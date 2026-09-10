# Experimental study runtime

Package 0.3 development; evidence schema 2; internal runtime protocol 0.4. Protocol and package versions are separate. Older studies remain readable but cannot resume under the new validation contract; start a new study instead.

## Dispatch loop

`study-start` collects evidence and starts/resumes an identical corpus. `study-next` returns one task. Submit every dispatched group exactly once in that response, then continue. The runtime makes no model calls.

| Task | Required work |
|---|---|
| PASS_A_BATCH | Analyze each group independently; propose 0–3 typed, paired observations or mark source escalation |
| PASS_B_CONSOLIDATE | Consolidate compatible changed proposals; preserve ADDED/REMOVED/MODIFIED direction |
| VERIFY_MOTIF | Decide YES/NO/UNCERTAIN for every dispatched member; YES supplies its own checked pair |
| FINAL_REPORT | Submit optional analyst notes; the runtime generates the authoritative report |
| COMPLETE | Read generated artifacts and disclose unresolved coverage |

Exact task ids and payload bindings matter. An identical resubmission is idempotent. A conflicting answer is rejected unless deliberately replaced with `--force`; validated upstream replacement invalidates dependent results and changes downstream task generations. Previously dispatched stale answers are rejected.

## Coverage and guardrails

Pass A defaults to 8 groups per batch (configurable 4–12), persisted at creation. At most 250 evidence groups are selected deterministically; the manifest reports sampling and the original available count.

A semantic group contains one distinct normalized candidate, plus duplicate occurrences. It is not a fuzzy browsing cluster. Missing comparison evidence or a truncated diff cannot count as analyzed through an unsupported NO response. Read both full snapshots and provide review citations, or submit explicit source escalation.

Recurring proposals require at least three verified YES groups across at least three representative repositories, with no one repository contributing more than half the groups. Every proposed member is verified in chunks of at most eight. NO/UNCERTAIN count toward the rejection share; over 20% is suppressed. Above fifteen proposed members, the proposal is suppressed as SPLIT_REQUIRED. Automatic split iterations are not implemented.

These are corpus guardrails, not proof of semantic accuracy or independent adoption.

## Persistence

```text
<workspace>/.skillvariants/studies/<study-id>/
  manifest.json             target, corpus fingerprint, protocol, counts, dispatches
  evidence.json             selected paired comparisons and occurrences
  snapshots/<raw-sha>.md     owned raw sources when available and hash-verified
  batches.json
  pass-a/                   submitted batches
  pass-a-merged.json
  pass-b-proposed.json
  verification/             per-motif member decisions
  motifs.json               accepted and suppressed proposals
  report.json / report.md   engine-generated artifacts
  analyst-notes.md          optional unverified agent prose
  events.jsonl
```

The study id binds target/source content, selected candidate content and occurrence provenance, and validation protocol. Changing only capture time or cache path does not create a new corpus. Changed content or corpus creates a new study and preserves the old one.

Creation is staged and atomically published. A per-study process lock serializes transitions; a rollback journal restores mutable artifacts after a failed or interrupted transition. A busy study fails with an actionable message rather than racing another writer. The transaction protects local process interruption; it is not a backup against disk loss or manual tampering.

## Completion and errors

COMPLETE requires readable report artifacts. If completed artifacts are missing, the runtime raises an integrity error. A no-motif study still writes an explicit empty report.

`groups_submitted`, `groups_analyzed`, `groups_unresolved` and `groups_pending` distinguish submitted responses, source-resolved analysis, unresolved source material and missing submissions. Completion can include unresolved sources and does not imply full GitHub coverage.

Acquisition errors fail before publishing a partial study. Retry with the same cache settings after resolving the error. Use `--offline` before the command to read cached data only. Use `--refresh` before the command to capture current sources. Both options together are rejected.
