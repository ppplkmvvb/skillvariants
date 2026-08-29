# Runtime Report — Agent Study Runtime v0.2

**Verdict: `STUDY_RUNTIME_GO`**

All runtime QA gates pass. One user-style request per family drove the full
loop (study-start → study-next/submit → COMPLETE → report) with zero manual
file surgery. Interrupt/resume, idempotent resubmission, malformed-submission
rejection, artifact integrity, source-URL preservation, and unstable-motif
suppression were all verified.

## 1. Verdict

`STUDY_RUNTIME_GO`.

## 2. Architecture

```text
Agent Skill (SKILL.md, six-step loop)
  ↓  study-start / study-next / study-submit / study-report
Study Runtime (skillvariants/study/: models, storage, tasks, runtime,
               reporting — state machine, atomic persistence, guardrail)
  ↓
SkillVariants Core (deterministic evidence, grouping, recurrence)
  ↓
Agent semantic tasks (PASS A batches, PASS B consolidation, verifier)
  ↓
Accepted recurring motifs → final study report
```

The agent reasons; the Core owns state, facts, counts, validation, and
recovery. No hosted model integration: the runtime is model-agnostic.

## 3. State model

Statuses: `CREATED → EVIDENCE_READY → PASS_A_IN_PROGRESS →
PASS_A_COMPLETE → (PASS_B_READY) → PASS_B_COMPLETE → VERIFYING → COMPLETE`,
plus `FAILED_RECOVERABLE`, `FAILED_TERMINAL`, `TARGET_CHANGED`.

Study id = `<skill-name>-<hash7>` from target URL + normalized content hash +
runtime version. Same content resumes; changed content creates a new study
and marks the old one superseded. Sessions persist under
`.skillvariants/studies/<study-id>/` with atomic JSON writes
(temp-file + os.replace) and an append-only `events.jsonl` audit log
(local-only, no secrets, no telemetry).

## 4. Task protocol

`study-next` returns exactly one task:
`PASS_A_BATCH` | `PASS_B_CONSOLIDATE` | `VERIFY_MOTIF` | `FINAL_REPORT` |
`COMPLETE`. Each payload is self-contained (groups include
`direct_skill_url` and a ready-made `compare_command`). `study-submit`
validates task/study ids, group membership, enums, invariants (vague
invariants rejected), behavior signatures, and fingerprints before
advancing. Malformed submissions never advance state.

## 5. PASS A batching

8 groups per batch (CLI `--batch-size` 4-12), deterministic group-ID order,
completed batches never rerun. Batch payloads expose no recurrence counts,
no other groups' labels, no canonical names.

## 6. PASS B orchestration

`PASS_B_CONSOLIDATE` is dispatched only after PASS A completes. The payload
contains the proposed motif actions, invariants, behavior signatures,
supporting group ids, and short evidence summaries — no counts, no benchmark
labels, no frequency ranking. The response is validated (labels, invariants,
signatures, group membership) before storage.

## 7. Verifier orchestration

Each proposed motif with ≥3 supporting groups produces a `VERIFY_MOTIF` task
(max 8 groups per task) containing only the invariant, behavior signature,
and group evidence. Decisions YES/NO/UNCERTAIN are validated and persisted
per motif. Acceptance rules enforced by `consolidation.accept_cluster`:
YES groups ≥3, YES repos ≥3, single repo ≤50%, UNCERTAIN excluded,
rejection rate (NO+UNCERTAIN)/proposed ≤20% → else `UNSTABLE` (one split
iteration allowed; otherwise suppressed as unresolved).

## 8. Failure recovery

Verified by tests: malformed submissions (unknown group id, bad enum, empty
or vague invariant) are rejected without advancing state; identical
resubmission is idempotent; conflicting resubmission requires `--force`;
GitHub failures surface as actionable CLI errors and leave the study in a
recoverable state.

## 9. Resume test

A study was interrupted after 2 PASS A batches (16 groups analyzed); a fresh
runtime instance resumed with `study-next` returning `pass-a-003` (the
third batch), and completed normally. Verified in
`research/runtime-v0.2/qa-gates.json`.

## 10. Idempotency test

Resubmitting an already-submitted batch (byte-identical) returns
`IDEMPOTENT` and does not advance counts; a conflicting resubmission is
rejected without `--force`.

## 11. Per-family dogfood

Driven end-to-end through the real CLI (`dogfood_driver.py`), with semantic
answers supplied by the frozen guardrail-benchmark artifacts:

| Family | Batches | Verifier tasks | Final status | Accepted motifs |
|---|---:|---:|---|---:|
| systematic-debugging | 11 | 9 | COMPLETE | 8 |
| frontend-design | 9 | 3 | COMPLETE | 3 |
| brainstorming | 12 | 7 | COMPLETE | 7 |

Artifacts per family: `manifest.json`, `motifs.json`, `report.json`,
`report.md`, `events.jsonl` under `research/runtime-v0.2/<family>/`.

## 12. Final artifact integrity

For all three families: statuses `COMPLETE`; accepted counts consistent
across manifest/motifs/report; every supporting group carries a valid
`https://github.com/...SKILL.md` direct URL; no UNSTABLE/UNRESOLVED motif
leaked into accepted; report.md contains all required sections and no
forbidden phrasing ("best practice", "widely adopted", etc.); events.jsonl
parses line-by-line. **Integrity check: PASS.**

## 13. Remaining runtime risks

1. Long studies need many agent turns (12 batches for brainstorming); a
   `--resume`-friendly workflow is essential and now exists.
2. Cross-family motif clusters are split per family in the runtime; a future
   cross-family study mode could aggregate across studies.
3. The driver replayed frozen semantic answers for QA; a live third-party
   agent may produce different (worse or better) proposals — the guardrail,
   not the driver, is the quality gate.

## 14. Product implications

- The Agent Skill is now a thin six-step loop; all protocol complexity lives
  in the runtime and is covered by tests.
- Next: Agent Skill polish, human CLI UX, web explorer over
  `.skillvariants/studies/` artifacts, README/demo, v0.2 release.

## 15. Verdict

**`STUDY_RUNTIME_GO`**
