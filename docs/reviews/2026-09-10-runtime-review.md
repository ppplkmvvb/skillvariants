# Independent runtime review — 2026-09-10

Reviewed the integrated `study/` runtime and `consolidation.py` without editing production code. Reproductions used original synthetic source documents, production `StudyRuntime.start/next_task/submit`, the production comparison builder, and isolated workspaces beneath `.test-tmp-review/`. Interpreter: `.venv-dev/Scripts/python.exe`.

The findings below describe the reviewed state, before subsequent root-agent fixes. They are independent of temporary legacy-fixture failures. Reproduction outputs are retained locally in `runtime-review-results.json`, `concurrency-review-results.json`, and `quote-review-results.json` beneath `.test-tmp-review/`.

## P1 — Candidate changes are discarded when an unchanged target resumes

**Locations:** `src/skillvariants/study/runtime.py:53`; `src/skillvariants/study/models.py:60`.

`start()` collects fresh evidence but decides whether to resume solely from target identity and target content. Candidate source identities, candidate hashes, selected membership and retrieval scope do not participate. A refresh that discovers changed candidates therefore returns the old study and silently discards the fresh corpus.

**Reproduced:** start with three candidates; change candidate content while keeping the target unchanged; start again. The second call returned the same study id with `resumed: true`. The freshly collected first-candidate hash was `4111f36a…`, but persisted evidence retained `55d40e72…` from the first collection.

**Correction:** bind new-study/resume identity to a canonical corpus snapshot fingerprint as well as target source/content and protocol. Include occurrence/source identity, raw/normalized content identity and sampling/retrieval scope; exclude volatile fetch timestamps/cache paths. A changed corpus should create a distinct study or return an explicit changed-corpus choice, rather than claiming to resume the new evidence.

## P1 — Truncated evidence can be counted as conclusively analyzed without any citation

**Location:** `src/skillvariants/study/tasks.py:93`.

Paired evidence is validated only inside the motif loop. A response with `meaningful_behavior_change: NO`, `motifs: []`, and `needs_source_escalation: false` bypasses evidence validation, even when the dispatched comparison is explicitly truncated and contains no hunks. This contradicts the dispatched escalation instructions and makes the coverage report misleading.

**Reproduced:** dispatch three comparisons created with `max_lines=1`, all with `truncated: true` and zero hunks. Submit the uncited NO response above for every group, then an empty Pass B. The study reached COMPLETE with `groups_analyzed: 3`, `groups_unresolved: 0` and `groups_pending: 0`.

**Correction:** unavailable/truncated evidence must remain unresolved unless the response supplies a validated full-source basis for its group-level determination. Apply this rule to negative/no-motif determinations as well as positive motifs. Merely setting an agent-provided boolean cannot establish source coverage.

## P1 — A crash after the final fingerprint prevents idempotent completion

**Locations:** `src/skillvariants/study/runtime.py:203`, `src/skillvariants/study/runtime.py:298`.

Final-report submission writes report artifacts and its fingerprint before saving COMPLETE in the manifest. If that last manifest write fails, the next identical submission exits through the generic idempotent shortcut, without repairing the state transition.

**Reproduced:** advance three legitimately cited groups through Pass A, Pass B and verification. Inject an `OSError` at `save_manifest` during final submission. Restore storage, resubmit the exact final response, then call `next_task`. Retry returned IDEMPOTENT; the manifest remained VERIFYING; `next_task` dispatched FINAL_REPORT again. Both report artifacts already existed. Repeating the same normal submit cannot finish the study.

**Correction:** commit submission outcome, fingerprint and state transition transactionally, or record an explicit recoverable transaction and replay its remaining effects. Idempotency must verify/reconcile the committed outcome rather than treating fingerprint existence as completion.

## P1 — Invalidated downstream task ids accept pre-revision responses after redispatch

**Locations:** `src/skillvariants/study/runtime.py:126`, `src/skillvariants/study/runtime.py:147`, `src/skillvariants/study/runtime.py:393`.

Dispatch identity contains a reused task id and basic membership, without an input fingerprint or generation. Force-replacing an upstream response removes old downstream state, but the next task receives the same id. A previously generated result can then be submitted against different upstream inputs.

**Reproduced:** dispatch `pass-b-001` after Pass A proposals saying “skip approval”; save its unsubmitted response. Force-replace Pass A proposals with “record deployment log.” The next task was again `pass-b-001`, now containing the new action. Submitting the saved pre-replacement Pass B response was ACCEPTED. Group ids and change direction were unchanged, so the structural validator could not detect staleness.

**Correction:** bind task identity and each submission to study id, protocol, input/corpus digest and upstream generation. Regenerated tasks must have a different immutable identity or require a matching dispatch digest. This addresses stale work; it does not imply an action’s semantic meaning can be checked by hashing.

## P1 — Concurrent conflicting submissions can both succeed without force

**Locations:** `src/skillvariants/study/runtime.py:193`; `src/skillvariants/study/storage.py:159`.

Read/check/write spans multiple independent files and has no per-study lock or revision compare-and-swap. Atomic individual JSON replacements do not protect the submission transaction.

**Reproduced:** two runtime instances submit different responses for the same dispatched Pass A task without force. Synchronize only their initial state loads, then let writer one commit fully before writer two continues using its already-loaded state. Both returned ACCEPTED; writer two silently overwrote writer one. The responses differed in a persisted notes field, so they had different fingerprints. An uncontrolled simultaneous write also produced a Windows access-denied replacement error.

**Correction:** serialize per-study mutation commands across processes or use optimistic revision checks covering the complete transaction. The second differing submission must be rejected as a conflict. Include dispatch, start/create and invalidation in the same concurrency design.

## P2 — Study-owned evidence does not retain the full source snapshots

**Locations:** `src/skillvariants/study/storage.py:113`; `src/skillvariants/study/evidence.py:40`.

`evidence.json` preserves `snapshot_path` values pointing to the external fetch cache; study creation never copies the raw source bytes into study-owned storage. The preserved snippets are intentionally bounded, so they cannot replace these files for escalation.

**Reproduced:** a valid full-source Pass A response initially passed validation. Start the study, remove only its test-owned external-cache snapshot files, and submit the same response through the runtime. It failed with “snapshot unavailable or invalid.” The study directory contained zero raw snapshot files. A copied study or routine cache cleanup has the same result.

**Correction:** archive hash-verified raw snapshots under the study, rewrite dispatched paths to those durable files, and retain all selected source identities. Persist explicit unavailable-source status where archival is impossible. Fetch cache retention must not determine whether an existing study can be verified offline.

## P2 — COMPLETE can advertise a report path that no longer exists

**Location:** `src/skillvariants/study/runtime.py:106`.

The COMPLETE fast path trusts the manifest without checking readable report artifacts.

**Reproduced:** complete a real synthetic study, remove only its test-owned `report.md`, then call `status` and `next_task`. Both still reported COMPLETE, and `next_task` returned the missing report path.

**Correction:** reconcile required artifacts when loading or returning completion. Regenerate deterministic artifacts when possible; otherwise return an explicit recoverable artifact error rather than a usable-completion signal.

## P2 — Arbitrary fabricated final narrative passes the report trust gate

**Location:** `src/skillvariants/study/runtime.py:543`; `src/skillvariants/study/reporting.py:22`.

The final narrative gate checks only whether five section names occur as substrings. The existing forbidden-phrase check is not called. Accepted semantic results are not bound to factual statements in the submitted narrative.

**Reproduced:** submit the required sections followed by “This is the best practice, widely adopted by 999999 independent teams.” The response was ACCEPTED, the study became COMPLETE, and the fabricated wording was stored in `report.md`.

**Correction:** prefer a deterministic report generated from accepted evidence/counts, with any free narrative explicitly separated as unverified commentary. Enforce the existing prohibited-claim rules as a narrow additional safeguard; a phrase blacklist by itself cannot establish factual support or semantic correctness.

## P2 — Malformed nested response fields escape as implementation exceptions

**Location:** `src/skillvariants/study/tasks.py:102`.

Several fields are used as strings before type validation. For example, motif `action` is immediately passed through `.strip()`.

**Reproduced:** take an otherwise valid cited Pass A response and set its first motif’s `action` to `["record audit"]`. `validate_pass_a_response` raised `AttributeError: 'list' object has no attribute 'strip'`, rather than `SubmissionError`. The CLI’s expected-error handler does not cover AttributeError.

**Correction:** validate nested field types before normalization and convert malformed submissions into actionable submission errors, preserving current state. Apply the same treatment to invariant, label, display name, notes, evidence summary, signature fields and report text.

## Architectural limits relevant to maturity

- Exact quote and hash validation establishes source quotation integrity, not whether a behavior was added, removed or equivalent. Direct forged quote text and wrong-side source hashes were rejected in the review. Nevertheless an accurately quoted passage can support a mistaken semantic interpretation; independent semantic evaluation remains necessary.
- The current multifile state store lacks a transaction/recovery and concurrent-writer contract. Individual atomic writes are useful but do not justify a crash-safe or concurrent-safe claim.
- Fresh retrieval, immutable corpus identity and durable source archival are separate concerns. Improving the fetch cache does not solve study reproducibility unless the selected corpus and bytes are committed with the study.
- Oversized canonical clusters are explicitly suppressed rather than automatically split, and unavailable/full-source evidence has a size limit. Those are acceptable experimental limits only when reports preserve the unresolved/suppressed scope instead of presenting the analyzed subset as exhaustive.

## Resolution review — current integrated runtime

A second independent review checked the integrated runtime, report renderer, paired-evidence validator and analyst-note storage. Production code was not edited during this review.

**Verified resolutions:** the original corpus/resume, durable-snapshot, crash-recovery, stale-task, concurrent-submission, missing-artifact, unsupported-negative-coverage, arbitrary-report-narrative and malformed-field findings are addressed by the current implementation. The final Markdown report now derives its counts, paired quotations and disposition from validated runtime artifacts; submitted prose is retained separately as unverified analyst notes.

**Validation:** `tests/test_runtime_durability.py`, `tests/test_runtime_integrity.py`, `tests/test_study_runtime.py`, `tests/test_report_evidence.py`, `tests/test_semantic_evidence.py` and `tests/test_evidence.py`: **92 passed in 118.29s**. Four additional independent production-runtime checks passed: malformed final notes preserve state; failure after replacing analyst notes restores the previous completed study; forcing empty notes removes old prose; and truncated negative review requires full-source citations on both sides. Results are retained locally in `.test-tmp-review/final-runtime-review-results.json`.

**Additional P2 found and resolved:** the reviewed `runtime.py` made every recognized verb-family mismatch a fatal cluster precheck. With genuine paired source text adding “Create an audit report before deployment,” a Pass A signature of “write an audit report” and canonical signature of “create an audit report” describe the same behavior, yet all three supporting groups were suppressed as `PRECHECK_FAILED`; `study-next` reached COMPLETE without a verifier task. The classifier places `write` in its allow family and `create` in its produce family. Reproduction: `.test-tmp-review/signature-synonym-review-results.json`.

The bounded correction removes broad verb-family mismatch from fatal prechecks and attaches a stable `verification_concern` to the relevant dispatched groups. That field includes the initial and canonical actions and explicitly says that the heuristic does not prove a contradiction; the verifier must judge their meaning using paired citations. Size, invariant and empty-action guards remain. `tests/test_runtime_signature_concerns.py` first failed because the next task was COMPLETE, then passed through verification to three groups across three repositories in the final report. The new test plus runtime-integrity, semantic-evidence and report-evidence suites passed: **56 passed in 44.13s**. No remaining P1/P2 was identified within this review's scope.

The remaining architectural limit is semantic: hash and quotation integrity do not establish that an interpretation follows from the text. The transaction checks cover process interruption and rollback; they are not evidence of resilience to filesystem or hardware failure.
