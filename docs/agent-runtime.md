# Agent Study Runtime (v0.2)

The Agent Study Runtime turns the validated research protocol into a
resumable, agent-driven workflow. The user asks one question; the agent
drives the runtime; the runtime owns state, validation, counts, and
recovery.

## Architecture

```text
Agent Skill (SKILL.md)
  ↓  study-start / study-next / study-submit / study-report
Study Runtime (state machine, atomic persistence, guardrail)
  ↓
SkillVariants Core (deterministic evidence + recurrence)
  ↓  semantic tasks: PASS A batches / PASS B consolidation / verifier
Agent (your coding agent) performs exactly one task at a time
  ↓
Accepted recurring motifs → final study report
```

The runtime is model-agnostic: no hosted LLM calls, no API keys. The
user's own agent provides all reasoning.

## Study session layout

```text
.skillvariants/studies/<study-id>/
├── manifest.json        # status, counts, target, sampling info
├── evidence.json        # deterministic evidence payload
├── batches.json         # PASS A batch dispatch/submission state
├── pass-a/batch-NNN.json
├── pass-a-merged.json
├── pass-b-proposed.json
├── verification/motif-*.json
├── motifs.json          # accepted + suppressed motifs (engine-computed)
├── report.json / report.md
└── events.jsonl         # local-only audit log
```

Study id: `<skill-name>-<hash7>` derived from target URL, normalized content
hash, and runtime version. A changed content hash creates a new study
(`TARGET_CHANGED`); the old study is preserved.

## CLI

```bash
uvx skillvariants study-start <SKILL.md-url> --json
uvx skillvariants study-status <study-id> --json
uvx skillvariants study-next  <study-id> --json
uvx skillvariants study-submit <study-id> <task-result.json>
uvx skillvariants study-report <study-id> --json
```

`study-next` returns exactly one task type:
`PASS_A_BATCH` | `PASS_B_CONSOLIDATE` | `VERIFY_MOTIF` | `FINAL_REPORT` |
`COMPLETE`.

`study-submit` validates task/study ids, group membership, enums, invariants
(vague invariants rejected), behavior signatures, and duplicate/conflicting
submissions. Identical resubmission is idempotent; conflicting resubmission
requires `--force`.

## Guardrail integration

The runtime enforces the consolidation guardrail deterministically:

- vague invariants rejected at submission time
- behavior-signature verb-family conflicts flagged before verification
- clusters >8 groups: mandatory verifier; >15: mandatory split proposal
- verifier NO/UNCERTAIN removes groups from recurrence
- rejection rate (NO+UNCERTAIN)/proposed > 20% → `UNSTABLE`: one split
  iteration allowed, otherwise suppressed as unresolved
- only ACCEPTED clusters appear in `motifs.json` as recurring

## Limits and sampling

Defaults: 8 groups per PASS A batch (4-12), max 250 semantic groups per
study, max 8 groups per verifier task, 1 split iteration. Above 250 groups
the runtime deterministically samples and discloses
`sampling_applied: true` with `semantic_groups_analyzed` vs
`total_groups_available`.

## Failure recovery

| Failure | Behavior |
|---|---|
| GitHub/network failure during start | `FAILED_RECOVERABLE`; rerun study-start |
| Malformed submission | rejected; state does not advance |
| Identical duplicate submission | idempotent (`IDEMPOTENT`) |
| Conflicting duplicate | rejected unless `--force` |
| Target content changed | new study; old preserved |
| No motif passes the guardrail | `COMPLETE` with empty motif list |
