# Agent Acceptance — v0.2.0

## Method

The agent acceptance test drives the study runtime through its real CLI
surface (subprocess calls, exactly as an external coding agent would), with
semantic answers supplied from the frozen guardrail-benchmark artifacts. The
test validates **orchestration autonomy**: the agent performs only semantic
work and never touches study state, task ids beyond the returned task, or
internal files.

## Test 1 — systematic-debugging

```text
Prompt: Study how this Skill has been adapted across GitHub: <URL>
→ study-start (EVIDENCE_READY)
→ 11 × (study-next PASS_A_BATCH → analyze → study-submit ACCEPTED)
→ 1 × PASS_B_CONSOLIDATE (behavior-equivalent clusters)
→ 9 × VERIFY_MOTIF (per-group YES/NO/UNCERTAIN)
→ FINAL_REPORT submitted with required sections
→ COMPLETE; report.json + report.md written by the runtime
```

Follow-up compare: `skillvariants compare <target> <variant> --json`
resolved with structural summary and source links.

## Test 2 — frontend-design

Same loop: 9 batches, 3 verifier tasks, COMPLETE, 3 accepted motifs.

## Results

| Requirement | Result |
|---|---|
| study starts autonomously from one request | PASS |
| agent completes the runtime loop without manual JSON editing | PASS |
| no user intervention for task ids (runtime returns them) | PASS |
| final answer contains accepted motifs | PASS (8 / 3) |
| counts come from the runtime (never the model) | PASS |
| exact sources appear (direct SKILL.md URLs) | PASS |
| follow-up compare works | PASS |

Same-model contamination from the benchmark author is disclosed in the
semantic report; orchestration autonomy itself does not depend on the model
identity (the runtime rejects any non-conforming submission).
