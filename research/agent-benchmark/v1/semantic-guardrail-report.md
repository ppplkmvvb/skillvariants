# Semantic Consolidation Guardrail Report — v1

**Verdict: `SEMANTIC_GUARDRAIL_GO`**

The guardrail fixed the single failure mode from the previous benchmark:
over-merge dropped from **26% (7/27) to 0% (0/18)** while all five
high-confidence reference motif families were retained and the pipeline
became fully deterministic at the acceptance layer. Evidence faithfulness
held at 100%, stability across two verifier runs is 100%, and the two
clusters that could not pass purity were suppressed by rule (UNSTABLE /
NON_RECURRING) instead of being rescued by broader invariants.

---

## 1. Verdict

`SEMANTIC_GUARDRAIL_GO` — agent semantic consolidation is reliable enough
for product-facing recurring motifs, with the invariant verification and
recurrence computation running deterministically.

## 2. Previous failure mode

v0 benchmark (`agent-semantic-report.md`): PASS B over-merged — 7/27
recurring motifs (26%) required semantic splitting. Worst case: a 26-group
`restructure-phases` cluster mixing phase renames, output contracts,
translation tiers, and methodology rewrites. Root cause: topic-similarity
clustering instead of behavior-equivalence clustering.

## 3. Guardrail design

Fixed architecture (section 2), one new deterministic module and one new
agent pass:

```text
Agent PASS A (frozen, unchanged: agent-pass-a.jsonl, 243 groups)
  ↓
Agent PASS B v2  — behavior-equivalence clustering with behavior_signature
  ↓
Deterministic precheck  — vague invariants, empty actions, size rules,
                          signature-family conflicts (consolidation.py)
  ↓
Independent verifier (agent) — per-group YES/NO/UNCERTAIN against the
                               cluster invariant, evidence only
  ↓
Deterministic acceptance — YES>=3 groups, >=3 repos, single repo <=50%,
                          UNCERTAIN excluded, rejection rate <=20%
  ↓
Unstable clusters: ONE split iteration → re-verify → else UNRESOLVED
  ↓
Deterministic recurrence counts (SkillVariants core semantics)
```

## 4. Behavior-signature schema

Every proposed canonical motif now carries:

```json
{
  "label": "add-explicit-hard-gate-implementation-lock",
  "invariant": "Adds an explicit, unavoidable prohibition on writing code or taking implementation action before approval.",
  "behavior_signature": {
    "trigger": "before explicit design approval",
    "action": "block implementation",
    "object": "code-writing/implementation",
    "outcome": "implementation only after gate"
  }
}
```

Deterministic conflict detection assigns each action to a behavior-verb
family (gate_stop / allow / produce / review / track / restructure /
delegate / announce / translate); two signatures conflict when their
families differ (negation-aware: "never write code" resolves to gate_stop).
Unknown verbs are not judged here — the verifier handles them.

## 5. Verifier design

One strict verifier pass (section 8): per group, decision YES/NO/UNCERTAIN
with a reason, seeing only the invariant and the group's evidence excerpts
— no aggregator rationale, no recurrence counts, no benchmark labels.
Same-model contamination from the baseline author is disclosed and applies
mainly to metric comparability, not to the structural audits.

## 6. Known over-merge regression cases (section 11)

Encoded as unit tests (`tests/test_consolidation.py`) at two layers:

- **Signature layer (must NOT auto-merge):** review-checklist vs
  DESIGN.md-before-code; planning-checklist vs scope-contract;
  traceability vs progress-tracking.
- **Positive controls (MUST merge):** stop-after-3-failures ≈ escalate ≈
  circuit-breaker; never-code ≈ block-coding ≈ forbid-implementation.
- **Pipeline layer:** a traceability cluster polluted with a
  progress-tracking group collapses below recurrence when the verifier
  rejects that member — proving the guardrail removes, not rescues.

All regression tests pass (suite total: 110 passed).

## 7. Benchmark metrics (section 12)

| Metric | v0 | v1 guarded | Target |
|---|---:|---:|---|
| A. Over-merge rate | 26% (7/27) | **0% (0/18)** | <15% (pref <10%) ✅ |
| B. Evidence faithfulness | 100% | **100%** (30 audited) | ≥95%, 0 fabricated ✅ |
| C. Strong-motif retention | — | **8/9 = 89%** | ≥80% ✅ |
| D. Stability (two verifier passes) | — | **100%** (86/86 member agreement) | ≥90% ✅ |

## 8. Per-family results (accepted recurring motifs)

| Family | Accepted motifs |
|---|---|
| systematic-debugging | stop-or-escalation (8g/8r), project-specific rules (7g/7r), route-verification (5g/5r), require-reproduction (4g/4r), feedback-loop (3g/3r), red-flags guard (4g/4r), preserve-root-cause-while-compressing (5g/5r), replace-with-named-methodology (4g/4r) |
| frontend-design | context-gathering-before-design (6g/6r), framework-specific rules (4g/4r), evaluation-or-review gate (4g/4r), brief-inference/ask-first gate (3g/3r) |
| brainstorming | hard-gate lock (6g/6r), ownership/handoff boundary (7g/7r), questioning protocol (7g/7r), diverge/converge split (3g/3r), greenfield-vs-existing split (3g/3r), stop-or-fallback (3g/3r) |

Cross-family clusters: context-gathering and project-specific rules span
FD+BS / SD+FD members respectively — recurrence counts respect family
boundaries per group.

## 9. Motifs split by the guardrail

The v1 over-merges were resolved at PASS B v2 design time by behavior
equivalence, then confirmed by the verifier:

- `restructure-phases` (26 groups) → split into **four** motifs:
  `preserve-root-cause-first-while-compressing` (5),
  `replace-with-named-methodology` (4), plus phase-rename and output-contract
  actions that fell below recurrence individually (correctly non-recurring).
- `add-evaluation-or-review-gate` → design-system-first workflow moved to
  its own motif (single group, non-recurring).
- `add-contract-scope-or-output-gates` → scope/trigger contract kept;
  DESIGN.md artifact split out; 4-step workflow and planning checklist
  rejected by the verifier (workflow ≠ contract).
- `add-project-specific-rules` → platform rendering rules moved out
  (single group).
- `add-aesthetic-philosophy-library` → discipline split moved out.
- `add-announcement-activation-gate` → split into announce-gate and
  when-not-to-use boundary.
- `add-one-hypothesis-at-a-time` → methodology rewrite moved to
  replace-with-named-methodology.

## 10. Motifs rejected as unstable / non-recurring

| Cluster | Status | Reason |
|---|---|---|
| add-routing-boundary-use-case | **UNSTABLE** (25% rejection) | SD#57 is positive routing, not a non-use boundary; verifier removed it, cluster fell to 3 YES / 4 proposed with 25% rejection > 20% |
| add-when-not-to-use-boundary | **NON_RECURRING** (33% rejection) | FD#9 is an activation paragraph, not a boundary; only 2 verified YES groups |

Per section 9/10, neither is displayed as recurring, neither had its
invariant broadened, and both remain available as UNRESOLVED candidates.

## 11. Stability rerun (section 12.D)

PASS B proposals were verified twice (run2 re-examined borderline groups;
two borderline verdicts tightened from UNCERTAIN to NO). Accepted-cluster
membership agreement: **86/86 = 100%** (target ≥90%). The two status
changes affected only non-accepted clusters.

## 12. Evidence-faithfulness audit (section 12.B)

30 verifier decisions sampled (seeded). Every decision reason was checked
against the group's frozen diff excerpts and the reviewer's source reading:
**30/30 supported; 0 fabricated repo/path/URL claims.** All URLs in outputs
are constructed by deterministic code from the evidence payload.

## 13. Remaining failure modes

1. **Recall cost of purity:** routing-boundary and when-not-to-use are real
   patterns but currently suppressed (3-4 groups with one off-member each).
   A future targeted re-cluster could recover them without broadening.
2. **Verifier dependence on excerpt truncation:** a few reasons cite
   headings truncated out of the 3-line excerpts; the verifier had to rely
   on the source reading pass. Longer structured excerpts would reduce this.
3. **Same-model contamination** on PASS A/B/verifier remains an upper-bound
   caveat for agreement-style metrics; structural audits are less affected.

## 14. Product implication

- `agent-recurring-motifs.json` is the product-facing motif source: 18
  accepted motifs, each with strict invariant, behavior signature,
  deterministic group/repo counts, and source URLs.
- The skill workflow must always run the invariant re-check + deterministic
  acceptance before presenting motifs; UNSTABLE/UNRESOLVED clusters are
  omitted, never broadened.
- Next phase (motif experience / web explorer) renders only accepted motifs.

## 15. Verdict

**`SEMANTIC_GUARDRAIL_GO`**

All gates pass: over-merge 0% (<15%), evidence faithfulness 100% (≥95%),
0 fabricated claims, high-confidence retention 89% (≥80%), stability 100%
(≥90%). Agent semantic consolidation is reliable enough for product-facing
recurring motifs. STOP — no web implementation in this run.
