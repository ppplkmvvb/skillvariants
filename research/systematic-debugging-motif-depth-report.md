# Depth Validation — systematic-debugging Mutation Motifs

**Verdict: `DEPTH_PARTIAL`**

Real, recurring, concrete mutation motifs exist in large numbers — 11 motifs
meet the recurrence threshold and the strongest ones are excellent. But the
strict DEPTH_GO gate (section 14) does not fully pass, and the non-passing
components point at one specific truth: much of the corpus is *maintainer/
researcher-caliber* adaptation rather than *your-own-debugging-skill-improver*
material. The explorer has depth; "Improve this Skill" should stay narrow or
experimental. See §13 for what this means for the product.

All evidence lives in `research/evidence-motifs/`:
`systematic-debugging-group-worksheet.tsv` (85 annotated group rows),
`group_records.json` / `group_records_annotated.json` (machine records,
`motif_aggregation.json`, `passb.txt`), and `motifs/*.md` (11 evidence cards
with direct SKILL.md URLs).

---

## 1. Corpus summary (spec section 3 — regenerated, not hard-coded)

| Measure | Value |
|---|---|
| Candidates found by code search | 267 |
| Unique related variants | 175 |
| Mutation groups (near-copy grouping) | 85 |
| Broad archetypes | 5 (compact-rewrite 34, workflow 30, routing 8, no-label 8, expanded 5) |
| Exact copies of the SKILL target | 1 occurrence collapsed |

Target skill: `obra/superpowers:skills/systematic-debugging/SKILL.md`.

## 2. Annotation method (sections 4-11, 6)

Flow: exports group representatives with deterministic signals
(`group_records.json`), then reading a human review bundle that contains, for
every group, its representative repo/path/ref, direct file URL, length delta,
added/removed headings/commands/references, routing/wrapper signals, and
added/removed text excerpts. Coding was done **group by group, in pool order,
before any frequency aggregation** (section 11), assigning:

- `meaningful_behavior_change`: YES / PARTIAL / NO
- `worth_reviewing`: YES / MAYBE / NO (judged on implementation quality only,
  popularity ignored)
- up to three free-form concrete `motif` labels per group (grammar:
  "Add ...", "Route ...", "Require ...", "Preserve ... while ...")

After coding, synonyms were normalized and consolidated; only semantically
equivalent implementations merged (e.g. "stop after 3 failed hypotheses" +
"stop and report after repeated failed attempts" → "add stop-or-escalation
after repeated failed fixes"). The full order is preserved in `annotate.py`
and `aggregate.py` for reproducibility.

## 3. How many groups contained meaningful behavioral changes

| Label | Groups |
|---|---|
| meaningful = YES | 71 |
| meaningful = PARTIAL | 7 |
| meaningful = NO | 7 |

77/85 groups carry at least one concrete motif label; 8 groups are
near-copy-only (no behavioral change beyond paragraph tuning).

## 4. Candidate motifs

75 free-form labels consolidated into 13 canonical motifs. Two fail the
recurrence threshold: `localize-skill-references` (2 groups) and
`translate-language-variant` (2 groups) — both are real but rare here.

## 5. Qualifying recurring motifs (≥3 groups, ≥3 repos, no repo >50%)

| Motif | Groups | Repos | Occurrences | Sem. consistency* | Worth=YES | Automation |
|---|---:|---:|---:|---:|---:|---|
| add stop-or-escalation after repeated failed fixes | 9 | 9 | 11 | 89% | **9/9** | PARTIAL |
| restructure phases or named workflow | 9 | 8 | 10 | 100% | 2/9 | PARTIAL |
| project-specific environment commands | 8 | 8 | 23 | 88% | 2/8 | EXISTING |
| route completion verification to separate skill | 5 | 5 | 19 | 80% | 4/5 | EXISTING |
| require reproduction before fixing | 5 | 5 | 21 | 100% | 0/5 | PARTIAL |
| preserve root-cause-first while compressing | 5 | 5 | 4 | 100% | 4/5 | EXISTING |
| add one-hypothesis-at-a-time | 4 | 4 | 5 | 100% | 2/4 | PARTIAL |
| add red-flags and anti-pattern guard | 4 | 4 | 6 | 50% | 3/4 | EXISTING |
| add routing-boundary use-case | 4 | 4 | 5 | 100% | 3/4 | EXISTING |
| add feedback-loop rule | 4 | 4 | 4 | 75% | **4/4** | EXISTING |
| explicitly declare purposes/goals | 3 | 3 | 4 | 100% | 0/3 | EXISTING |

\* consensus = fraction of supporting groups where the motif is the group's
*primary* (motif_1) label — the stricter reading of section 14.C.

**Automation column (PASS B, section 12-13):** EXISTING means the current
deterministic feature system directly contains usable signal (heading-name
match, routing-boundary phrase, command delta, cross-skill-ref delta,
length/rule preservation); PARTIAL means it needs a small generic phrase
detector to become reliable. No motif needs an LLM. Exploratory detector
recall on supporting groups: stop-or-escalation 1.0, reproduction 1.0,
red-flags 1.0, feedback-loop 0.75, routing-boundary 0.75, verification-route
0.20 (weak — it currently detects on body features poorly), project-commands
0.125 (weak; it needs the explicit rules-regex on descriptions).

## 6. Non-qualifying motifs and why

| Motif | Groups | Why excluded |
|---|---:|---|
| localize skill references (`superpowers:` → unqualified) | 2 | below ≥3-group floor; appears as cosmetic re-branding |
| translate language variant (German / Korean rebuilds) | 2 | below floor; likely single conversion stories, not a design change |

The eight near-copy-only groups were not motifs: they are the same four-phase
methodology re-worded with small paragraph edits.

## 7. Propagation / independence caveats (section 2, §8 report)

- The dominant source lineage (`obra/superpowers`) appears across many groups;
  "observed across N distinct groups" is a *recurrence* statement, not an
  ancestry claim or proof of independent invention.
- `generate` cluster check: max single-repo share per qualifying motif is
  33% (declare-purposes) and 25% for most; no motif is majority-derived from
  one repo (aggregate.py `max_repo_share <= 0.5`).
- One giant near-copy family (G1: 41 members, 101 occurrences, 1 pattern —
  Excuse/Reality table rework) carries *no* motif and is excluded from every
  supporting group, so no qualifying motif derives primarily from a single
  clone family. This satisfies section 14.F.
- aiskillstore/marketplace appears in three motifs' supporting groups — a
  marketplace where multiple skill *variants* coexist; each is a different
  file and classified independently, but this counts as one publisher across
  two motif families. This is the closest thing to a template-propagation
  cluster and it still does not dominate any single motif (>50% rule passes).

## 8. Developer usefulness review (section 14.D)

Ranking the five strongest motifs by #supporting groups (the strictest
reading):

| Rank | Motif | Worth=YES among representatives |
|---|---|---:|
| 1 | add stop-or-escalation | 9/9 |
| 2 | restructure phases | 2/9 |
| 3 | project-specific commands | 2/8 |
| 4 | route verification to separate skill | 4/5 |
| 5 | require reproduction | 0/5 |

Only 2/5 pass "majority worth=YES". The three that fail are precisely the
*adaptation-shape* motifs (restructure, project-specific, reproduction-rule)
— the representative implementations are genuine but feel like maintenance
variants rather than model practices worth opening. If ranked by worth=YES
instead, the top five become stop-or-escalation, route-verification,
feedback-loop, red-flags, preserve-root-cause-first — and 4/5 pass. The
honest reading: **the corpus contains a dense set of high-value motifs, but
they are mixed with a long tail of low-value restatements**, so a blanket
"majority of the five strongest" test is unstable.

## 9. Automation feasibility (PASS B, section 12-13)

Separating MOTIF EXISTS from AUTOMATION READY:

| Motif | Exists? | Automatable today? |
|---|---|---|
| stop-or-escalation | YES | PARTIAL — needs small generic escaped-loop detector (3-fix / circuit-breaker / escalation phrases). High recall (1.0 on supports). |
| red-flags guard | YES | EXISTING — heading match ("Red Flags") works; wording varies. |
| feedback-loop rule | YES | EXISTING — "Feedback Loop" heading match; two non-heading variants miss. |
| verification-route | YES | PARTIAL — cross-skill ref delta + verification terms; current detector recall 0.2, needs routing boundary + verification phrase combo. |
| project-specific commands | YES | PARTIAL — command delta already exists (EXISTING-class signal), but per-repo-rule detection needs the existing project-phrase regex widened. |
| restructure / preserve-root-cause | YES | EXISTING (heading turnover) / EXISTING (ALL-CAPS rule preservation + length). |

No MFCC-like learning or embedding is needed; all six top motifs can be
expressed in ≤10 lines of deterministic phrase/heading regex plus existing
features. But note "automation feasibility weak" applies to the **long tail**
of adaptation-shape motifs — they need designer input.

## 10. Deepest insight discovered (section 14.G)

The corpus converges on a **failure-handling escape hatch**: the base
Superpowers skill is prescriptive and has no termination policy. Repeatedly,
across 9 distinct groups, developers added an explicit stop/escalation rule
("after 3 failed fixes, STOP and question the architecture", "Three-fix
circuit breaker", "Escalation: 3+ Failed Fixes") while **keeping** the
root-cause-first law. The base text says *keep investigating*; the most
common human edit is *"keep investigating — but with an exit"*. That pairs
with a second, complementary policy: separating *root-cause finding* from
*completion verification* by routing the latter to a separate verification
skill (evidence: archive-level `verification-before-completion` naming in
several repos). Together this is a coherent, non-mechanical story: **the
methodology was adopted but its runaway-loop failure mode was patched by
userland**, which is exactly the kind of insight `git diff` cannot surface
and a registry cannot provide.

## 11. Strongest counterexample to the thesis

`add-routing-boundary-use-case` (4 groups, 4 repos) — labels "routing" where
the underlying change is often a use-case containment boundary ("Emergency
Stop Rule", "Refuse Gate", "do not use outside debugging"), not delegation.
If we require *true delegation* (cross-skill refs added), the motif nearly
collapses to verification-route. This is the clearest warning that **the
grouping step admits near-miss motif clusters** and that a future motif
detector must distinguish containment language from delegation language.

## 12. What this means for SkillVariants

- Not "Improve this Skill" (patch-recommendation layer) — the long tail of
  adaptation-shape variants are maintenance-grade and would be poor
  recommendations.
- Strong direction: **Community evolution / maintainer research explorer**
  — surfacing *recurrent adaptation policies* (stop-or-escalation,
  verification separation, red-flags guard, feedback-loop instrumentation)
  with linked implementations and a deterministic filter layer.
- PASS B says the strongest six motifs are cheap to surface with existing
  deterministic features plus a few small detectors — no LLM needed. The
  second product step (if taken) should be a `--motifs` hint layer, not a
  patch generator.

## 13. DEPTH_GO assessment vs. DEPTH_PARTIAL

| Gate | Meets? |
|---|---:|
| A. ≥5 recurring motifs | PASS (11) |
| B. 4/5 concrete (not "shorter/workflow changed") | PASS (top-5 all concrete) |
| C. ≥80% semantic consistency per motif | Most pass; 2 motifs below (red-flags 50%, feedback-loop 75%) → FAILS strictly for those two |
| D. 4/5 strongest have majority worth=YES | FAILS under group-count ranking (2/5); PASSES under worth-ranked (4/5) |
| E. ≥3 linked implementations per motif | PASS (all ≥3, with direct URLs) |
| F. no fake convergence | PASS (max single-repo share ≤33%, giant family carries no motifs) |
| G. non-trivial insight | PASS (runaway-loop escape hatch + verification separation policy) |

Because C (strictly) and D (under the strictest ranking) fail, the honest
verdict is **DEPTH_PARTIAL**, not DEPTH_GO.

---

## 14. Required summary table (section 17)

| Motif | Groups | Repos | Sem. consistency | Worth reviewing | Automation feasibility |
|---|---:|---:|---:|---:|---|
| add stop-or-escalation after repeated failed fixes | 9 | 9 | 89% | YES (9/9) | PARTIAL |
| restructure phases or named workflow | 9 | 8 | 100% | MAYBE (2/9) | PARTIAL |
| project-specific environment commands | 8 | 8 | 88% | MAYBE (2/8) | EXISTING |
| route completion verification to separate skill | 5 | 5 | 80% | YES (4/5) | PARTIAL |
| require reproduction before fixing | 5 | 5 | 100% | NO (0/5 WORTH) | PARTIAL |
| preserve root-cause-first while compressing | 5 | 5 | 100% | YES (4/5) | EXISTING |
| add one-hypothesis-at-a-time | 4 | 4 | 100% | PARTIAL (2/4) | PARTIAL |
| add red-flags and anti-pattern guard | 4 | 4 | 50% | YES (3/4) | EXISTING |
| add routing-boundary use-case | 4 | 4 | 100% | YES (3/4) | EXISTING |
| add feedback-loop rule | 4 | 4 | 75% | YES (4/4) | EXISTING |
| explicitly declare purposes/goals | 3 | 3 | 100% | PARTIAL (0/3) | EXISTING |

Summary numbers:

```
Total mutation groups reviewed          85
Meaningful=YES / PARTIAL / NO           71 / 7 / 7
Candidate motifs                       13
Meeting recurrence threshold            11
Meeting full DEPTH_GO quality bar       9 (2 fail consensus >=80%)
```

## 15. Required source-link convention

Every representative adaptation in the report cards carries
`direct_skill_url` in `research/evidence-motifs/motifs/*.md` with exact
repo, file path, and ref so a reader can go claim → representative → real
source without searching. All original groups retain their clickable URLs in
`systematic-debugging-group-worksheet.tsv`.

---

### Verdict

**DEPTH_PARTIAL.** The pipeline does reveal concrete, recurring,
developer-actionable motifs (the escape-hatch + verification-separation pair
being the headline finding), and automation feasibility for the strongest six
is high with no LLM. But the corpus also contains a large tail of
adaptation-shape restatements that are maintainer-caliber, several motifs
drop below the 80% semantic-consistency bar, and the majority-worthness test
is unstable. Recommended next product step: **keep SkillVariants as a
variant explorer / ecosystem research tool and add a `--motifs`-style
deterministic recurrent-pattern layer** — do not build the
patch-recommendation "Improve this Skill" system yet.
