"""PASS A annotation for cross-family falsification (frontend-design,
brainstorming). Coding happened from the per-family review bundles BEFORE any
frequency aggregation. Each group: (meaningful, worth_reviewing, [motifs]).
Motifs are concrete-action phrases; canonical consolidation happens after.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent

FD_CODING = {
    1: ("NO", "NO", []),
    2: ("PARTIAL", "MAYBE", ["Replace persona framing with generic anti-slop guidelines (template propagation)"]),
    3: ("YES", "YES", ["Add context-gathering protocol before design direction"]),
    4: ("YES", "YES", ["Add quantitative design-scoring formula (DFII)"]),
    5: ("YES", "YES", ["Add mandatory ask-before-assuming gate", "Add selective-reading tool routing"]),
    6: ("PARTIAL", "MAYBE", ["Add intake-copy packaging with routing headers"]),
    7: ("PARTIAL", "MAYBE", ["Adopt anti-slop guidelines template"]),
    8: ("YES", "MAYBE", ["Add explicit inputs-to-gather-or-assume contract"]),
    9: ("NO", "PARTIAL", ["Add when-to-activate trigger paragraph"]),
    10: ("YES", "YES", ["Add project-specific context loading (PROJECT_CONTEXT.md)"]),
    11: ("YES", "YES", ["Convert process into explicit ordered steps with design-before-code gates"]),
    12: ("PARTIAL", "NO", ["Rewrite as persona/mentorship guide"]),
    13: ("YES", "YES", ["Add framework-specific design rules (shadcn/ui)"]),
    14: ("YES", "YES", ["Add domain-specific rules (data-viz/dashboard)"]),
    15: ("YES", "PARTIAL", ["Add evaluation suite and delivery gate"]),
    16: ("NO", "NO", []),
    17: ("YES", "YES", ["Add framework-specific implementation rules (React/Next.js)"]),
    18: ("YES", "MAYBE", ["Add mandatory repo-sync-before-edits rule"]),
    19: ("YES", "PARTIAL", ["Add install instructions"]),
    20: ("YES", "PARTIAL", ["Add platform-specific rendering rules (mobile/safari + design-system doc link)"]),
    21: ("NO", "NO", []),
    22: ("PARTIAL", "NO", ["Add benchmark-dataset packaging"]),
    23: ("YES", "YES", ["Add product-specific design language and stack rules (Spendly)"]),
    24: ("YES", "YES", ["Add curated aesthetic-philosophy library"]),
    25: ("NO", "NO", []),
    26: ("YES", "YES", ["Add decision-tree and spacing-system quick reference"]),
    27: ("NO", "PARTIAL", []),
    28: ("NO", "NO", []),
    29: ("YES", "YES", ["Add design-system reuse-before-create rules"]),
    30: ("YES", "MAYBE", ["Add context-detection and authority hierarchy before design"]),
    31: ("NO", "NO", []),
    32: ("YES", "PARTIAL", ["Add numbered iron-law requirements"]),
    33: ("YES", "YES", ["Add phase-0 design-thinking gate with do/don't table"]),
    34: ("YES", "PARTIAL", ["Add source/license attribution header + adaptation note"]),
    35: ("NO", "NO", []),
    36: ("YES", "YES", ["Add skill-scope contract (when-to-use/scope/included/excluded/inputs)"]),
    37: ("YES", "MAYBE", ["Fuse two source skills into combined edition"]),
    38: ("NO", "PARTIAL", []),
    39: ("YES", "PARTIAL", ["Reorder workflow: frame interface before visual system"]),
    40: ("YES", "YES", ["Add design-system-first workflow (system before UI)"]),
    41: ("YES", "PARTIAL", ["Add 4-step definition/constraint/implement/refine workflow"]),
    42: ("NO", "NO", []),
    43: ("YES", "YES", ["Add accessibility-first and semantic-HTML scaffolding rules"]),
    44: ("YES", "YES", ["Split skill into product/UX/visual design disciplines"]),
    45: ("PARTIAL", "MAYBE", ["Add huge mega-file with brief-inference mandator (absorber)"]),
    46: ("NO", "NO", []),
    47: ("NO", "NO", []),
    48: ("YES", "YES", ["Add ordered-levers hierarchy and invariant rules"]),
    49: ("YES", "YES", ["Add trigger/do-not-use/output-contract guardrails"]),
    50: ("YES", "MAYBE", ["Add attribution header to trimmed rewrite"]),
    51: ("NO", "PARTIAL", []),
    52: ("YES", "YES", ["Add machine-readable design contract (DESIGN.md) before implementation"]),
    53: ("NO", "PARTIAL", []),
    54: ("YES", "PARTIAL", ["Add pre-implementation planning checklist"]),
    55: ("PARTIAL", "MAYBE", ["Add style-variant routing table and brief inference (in absorber mega-file)"]),
    56: ("YES", "PARTIAL", ["Add 5-section flagship blueprint"]),
    57: ("YES", "YES", ["Add technology-stack priority ordering rules"]),
    58: ("YES", "YES", ["Add verify + visual-discipline output contract"]),
    59: ("YES", "YES", ["Add finance-domain-specific design rules"]),
    60: ("NO", "NO", []),
    61: ("NO", "NO", []),
    62: ("YES", "YES", ["Add review checklist and migration note"]),
    63: ("YES", "YES", ["Add canonical-path compatibility wrapper redirect"]),
    64: ("YES", "PARTIAL", ["Adapt to framework-specific (Vue) application"]),
    65: ("PARTIAL", "NO", []),
    66: ("YES", "MAYBE", ["Add extreme-tone commitment rule"]),
    67: ("PARTIAL", "NO", []),
    68: ("YES", "YES", ["Add style-selector pre-gate before any screen work"]),
}

BS_CODING = {
    1: ("YES", "YES", ["Add workflow-mode guard gate"]),
    2: ("PARTIAL", "MAYBE", ["Simplify to overview/process/after-design template (propagation)"]),
    3: ("PARTIAL", "MAYBE", ["Adopt checklist/process-flow template (propagation)"]),
    4: ("YES", "YES", ["Add mandatory non-functional-requirements phase"]),
    5: ("NO", "NO", []),
    6: ("YES", "YES", ["Add explicit phase split with worktree handoff"]),
    7: ("NO", "NO", []),
    8: ("YES", "MAYBE", ["Add provenance/source annotations and thin wrapper"]),
    9: ("YES", "YES", ["Add greenfield-project specialization path"]),
    10: ("YES", "YES", ["Add environment-availability (prompt-prefix) trigger guard"]),
    11: ("YES", "YES", ["Add rationalization catalogue and post-violation recovery"]),
    12: ("YES", "YES", ["Add planner-handoff output boundary"]),
    13: ("YES", "MAYBE", ["Add session-detection preamble and completion status"]),
    14: ("NO", "NO", []),
    15: ("YES", "YES", ["Add greenfield bootstrap path and domain-language register"]),
    16: ("YES", "PARTIAL", ["Add TBDs log and reporting model"]),
    17: ("YES", "YES", ["Add progress-tracking and when-to-use contract"]),
    18: ("YES", "PARTIAL", ["Reorder to when-to-use/how-to-use structure"]),
    19: ("NO", "PARTIAL", []),
    20: ("YES", "YES", ["Add related-skill routing (worktrees/plans)"]),
    21: ("YES", "YES", ["Add existing-codebase-specific working rules"]),
    22: ("NO", "NO", []),
    23: ("YES", "PARTIAL", ["Add goal/design-review/after-approval structure"]),
    24: ("YES", "YES", ["Add multi-phase gates (hard gate/research gate/spec self-review)"]),
    25: ("YES", "YES", ["Add ownership and required-output contract"]),
    26: ("YES", "PARTIAL", ["Add when-to-use/when-not-to-use boundary"]),
    27: ("YES", "PARTIAL", ["Add save-location rule and questioning rules"]),
    28: ("YES", "PARTIAL", ["Add 5-phase structure with design-documentation phase"]),
    29: ("YES", "YES", ["Add explicit hard-gate implementation lock"]),
    30: ("YES", "YES", ["Add explicit hard-gate implementation lock"]),
    31: ("YES", "MAYBE", ["Add project-conventions application rules"]),
    32: ("YES", "YES", ["Add problem/solution/user-stories spec structure"]),
    33: ("NO", "NO", []),
    34: ("YES", "YES", ["Add requirement-traceability hard rule (B#/F#)"]),
    35: ("YES", "YES", ["Add stop conditions and fallback path"]),
    36: ("YES", "YES", ["Add interactive-tool (AskUserQuestion) usage protocol"]),
    37: ("YES", "PARTIAL", ["Add one-question-at-a-time dialogue rules"]),
    38: ("YES", "MAYBE", ["Add lite-output tier with bilingual adaptation"]),
    39: ("YES", "YES", ["Add scale guard for process depth"]),
    40: ("NO", "PARTIAL", []),
    41: ("YES", "PARTIAL", ["Add tool-parameter contract for ask_questions"]),
    42: ("YES", "YES", ["Add mandatory skill-chain and session-resumption protocol"]),
    43: ("YES", "PARTIAL", ["Add use-when/do-not-use boundary"]),
    44: ("YES", "YES", ["Add explicit hard-gate implementation lock", "Add single-output handoff (agreed design only)"]),
    45: ("YES", "YES", ["Add design/challenge mode split"]),
    46: ("YES", "YES", ["Add ownership/delegation boundary"]),
    47: ("YES", "PARTIAL", ["Add comprehensive question-generation analysis"]),
    48: ("YES", "MAYBE", ["Add anti-pattern catalogue and task-spec output"]),
    49: ("YES", "YES", ["Add reframe-before-you-build phase"]),
    50: ("YES", "YES", ["Add explicit hard-gate implementation lock"]),
    51: ("YES", "PARTIAL", ["Add agent-assignment output contract"]),
    52: ("YES", "YES", ["Add project-document-first rules (DESIGN/PRD/GOAL)"]),
    53: ("NO", "PARTIAL", []),
    54: ("YES", "YES", ["Add mandatory brainstorming-report and red-flag stop"]),
    55: ("YES", "YES", ["Add proportional-depth scaling with premortem check"]),
    56: ("NO", "NO", []),
    57: ("YES", "PARTIAL", ["Add restate-goal and missing-constraints step"]),
    58: ("YES", "YES", ["Add explicit diverge/converge two-phase split"]),
    59: ("YES", "PARTIAL", ["Translate bilingual and add decision-tree companion"]),
    60: ("YES", "YES", ["Add hard gate with filesystem-first context and design-doc template"]),
    61: ("YES", "PARTIAL", ["Add open-ended-trigger and handoff"]),
    62: ("YES", "YES", ["Add one-question-at-a-time iron law"]),
    63: ("YES", "MAYBE", ["Add deep decision-tree interview protocol"]),
    64: ("YES", "YES", ["Add domain/architecture/security check gates (project-specific)"]),
    65: ("YES", "PARTIAL", ["Add validation-criteria phase"]),
    66: ("YES", "PARTIAL", ["Add when-to-trigger matrix and resources"]),
    67: ("NO", "PARTIAL", []),
    68: ("YES", "PARTIAL", ["Add trigger conditions and validate-in-sections"]),
    69: ("YES", "PARTIAL", ["Add conversation-technique protocol (one question/multiple choice)"]),
    70: ("YES", "PARTIAL", ["Add three-phase structure with approach comparison"]),
    71: ("YES", "PARTIAL", ["Add related-skill routing and quick start"]),
    72: ("YES", "YES", ["Add phase-gate stops (BLOCK/STOP) and routed entry points"]),
    73: ("YES", "PARTIAL", ["Add purpose boundary vs research"]),
    74: ("YES", "PARTIAL", ["Add entry flag and frame/options/design-doc steps"]),
    75: ("YES", "PARTIAL", ["Add restate/options-min-3/evaluate/commit process"]),
    76: ("YES", "YES", ["Add scope split with other skills (what vs how)"]),
    77: ("YES", "PARTIAL", ["Add design-before-code-always core principle"]),
    78: ("YES", "MAYBE", ["Add name-your-confusion step with optional deep research"]),
    79: ("YES", "YES", ["Add mandatory 3-questions enforcement gate"]),
    80: ("YES", "PARTIAL", ["Add frame/diverge/pressure-test/recommend flow"]),
    81: ("YES", "MAYBE", ["Add domain-reference lookup and safety-boundary rules"]),
    82: ("YES", "YES", ["Add explicit hard-gate implementation lock"]),
    83: ("YES", "PARTIAL", ["Add trigger-step design-document workflow"]),
    84: ("YES", "YES", ["Add explicit hard-gate implementation lock", "Translate bilingual"]),
    85: ("NO", "NO", []),
    86: ("YES", "MAYBE", ["Add facilitation-script/SME-invocation meta-layer with third-party notice"]),
    87: ("NO", "PARTIAL", []),
    88: ("YES", "PARTIAL", ["Add 7-phase todo structure with 5WH question framework"]),
    89: ("YES", "MAYBE", ["Add RFC-shaped output with discovery questions"]),
    90: ("YES", "PARTIAL", ["Add context-gathering and feature-structure template"]),
}

# Canonical consolidation (merge only semantically equivalent changes).
CANONICAL = {
    "add-explicit-hard-gate-implementation-lock": [
        "Add explicit hard-gate implementation lock",
    ],
    "add-context-gathering-before-design": [
        "Add context-gathering protocol before design direction",
        "Add context-detection and authority hierarchy before design",
    ],
    "add-framework-specific-design-rules": [
        "Add framework-specific design rules (shadcn/ui)",
        "Add framework-specific implementation rules (React/Next.js)",
        "Add design-system reuse-before-create rules",
        "Add decision-tree and spacing-system quick reference",
        "Add technology-stack priority ordering rules",
    ],
    "add-domain-specific-design-rules": [
        "Add domain-specific rules (data-viz/dashboard)",
        "Add finance-domain-specific design rules",
    ],
    "add-project-specific-rules": [
        "Add project-specific context loading (PROJECT_CONTEXT.md)",
        "Add product-specific design language and stack rules (Spendly)",
        "Add platform-specific rendering rules (mobile/safari + design-system doc link)",
        "Add domain/architecture/security check gates (project-specific)",
    ],
    "add-evaluation-or-review-gate": [
        "Add evaluation suite and delivery gate",
        "Add ordered-levers hierarchy and invariant rules",
        "Add verify + visual-discipline output contract",
        "Add review checklist and migration note",
        "Add design-system-first workflow (system before UI)",
    ],
    "add-contract-scope-or-output-gates": [
        "Add skill-scope contract (when-to-use/scope/included/excluded/inputs)",
        "Add trigger/do-not-use/output-contract guardrails",
        "Add machine-readable design contract (DESIGN.md) before implementation",
        "Add 4-step definition/constraint/implement/refine workflow",
        "Add pre-implementation planning checklist",
    ],
    "add-questioning-or-interaction-protocol": [
        "Add mandatory 3-questions enforcement gate",
        "Add interactive-tool (AskUserQuestion) usage protocol",
        "Add one-question-at-a-time dialogue rules",
        "Add one-question-at-a-time iron law",
        "Add conversation-technique protocol (one question/multiple choice)",
        "Add comprehensive question-generation analysis",
        "Add deep decision-tree interview protocol",
    ],
    "add-ownership-or-handoff-boundary": [
        "Add ownership and required-output contract",
        "Add ownership/delegation boundary",
        "Add planner-handoff output boundary",
        "Add related-skill routing (worktrees/plans)",
        "Add scope split with other skills (what vs how)",
        "Add single-output handoff (agreed design only)",
    ],
    "add-scale-guard-or-proportional-depth": [
        "Add scale guard for process depth",
        "Add proportional-depth scaling with premortem check",
    ],
    "add-environment-or-availability-guard": [
        "Add workflow-mode guard gate",
        "Add environment-availability (prompt-prefix) trigger guard",
        "Add when-to-use/when-not-to-use boundary",
    ],
    "add-project-document-first-rules": [
        "Add project-document-first rules (DESIGN/PRD/GOAL)",
        "Add project-conventions application rules",
    ],
    "add-greenfield-vs-existing-path-split": [
        "Add greenfield-project specialization path",
        "Add greenfield bootstrap path and domain-language register",
        "Add existing-codebase-specific working rules",
    ],
    "add-diverge-converge-phase-split": [
        "Add explicit diverge/converge two-phase split",
        "Add frame/diverge/pressure-test/recommend flow",
        "Add reframe-before-you-build phase",
        "Add 5-phase structure with design-documentation phase",
    ],
    "add-stop-or-fallback-condition": [
        "Add stop conditions and fallback path",
        "Add mandatory brainstorming-report and red-flag stop",
        "Add phase-gate stops (BLOCK/STOP) and routed entry points",
    ],
    "add-traceability-or-spec-output-rule": [
        "Add requirement-traceability hard rule (B#/F#)",
        "Add problem/solution/user-stories spec structure",
        "Add progress-tracking and when-to-use contract",
        "Add restate-goal and missing-constraints step",
    ],
    "add-adaptation-note-or-source-attribution": [
        "Add source/license attribution header + adaptation note",
        "Add attribution header to trimmed rewrite",
        "Add provenance/source annotations and thin wrapper",
        "Add facilitation-script/SME-invocation meta-layer with third-party notice",
    ],
    "compatibility-wrapper-redirect": [
        "Add canonical-path compatibility wrapper redirect",
    ],
    "wrapped-template-rewrite": [
        "Replace persona framing with generic anti-slop guidelines (template propagation)",
        "Adopt anti-slop guidelines template",
        "Simplify to overview/process/after-design template (propagation)",
        "Adopt checklist/process-flow template (propagation)",
    ],
}

FAMILIES = [
    ("frontend-design", FD_CODING, "frontend-design"),
    ("brainstorming", BS_CODING, "brainstorming"),
]


def main() -> None:
    for fam, coding, dirname in FAMILIES:
        recpath = BASE / dirname / f"{dirname}-group-records.json"
        rows = json.loads(recpath.read_text(encoding="utf-8"))
        for record in rows:
            gid = record["group_id"]
            meaning, worth, motifs = coding.get(gid, ("NO", "NO", []))
            record["meaningful_behavior_change"] = meaning
            record["worth_reviewing"] = worth
            record["motif_1"] = motifs[0] if motifs else ""
            record["motif_2"] = motifs[1] if len(motifs) > 1 else ""
            record["motif_3"] = motifs[2] if len(motifs) > 2 else ""
        (BASE / dirname / f"{dirname}-group-records-annotated.json").write_text(
            json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
        with (BASE / dirname / f"{dirname}-group-worksheet.tsv").open(
                "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
        print(fam, "meaningful:",
              Counter(r["meaningful_behavior_change"] for r in rows),
              "worth:", Counter(r["worth_reviewing"] for r in rows))

    # aggregate recurrence
    for fam, coding, dirname in FAMILIES:
        rows = json.loads((BASE / dirname / f"{dirname}-group-records-annotated.json")
                          .read_text(encoding="utf-8"))
        motif_groups: dict[str, set[int]] = defaultdict(set)
        motif_repo: dict[str, Counter] = defaultdict(Counter)
        for r in rows:
            labels = [r["motif_1"], r["motif_2"], r["motif_3"]]
            for label in [l for l in labels if l]:
                for canon, syns in CANONICAL.items():
                    if label in syns:
                        motif_groups[canon].add(r["group_id"])
                        motif_repo[canon][r["repository"]] += 1
        print(f"\n=== {fam} recurrence ===")
        for canon, groups in sorted(motif_groups.items(), key=lambda kv: -len(kv[1])):
            n_groups = len(groups)
            n_repos = len(motif_repo[canon])
            share = max(motif_repo[canon].values()) / n_groups if n_groups else 0
            worths = Counter(r["worth_reviewing"] for r in rows if r["group_id"] in groups)
            yes = worths.get("YES", 0)
            passes = n_groups >= 3 and n_repos >= 3 and share <= 0.5
            print(f"  {canon[:52]:52s} groups={n_groups:3d} repos={n_repos:3d} "
                  f"share={share:.0%} worthYES={yes}/{n_groups} {'PASS' if passes else 'FAIL'}")
        # strong: recurrence + majority worth=YES
        strong = [c for c, g in motif_groups.items()
                  if len(g) >= 3 and len(motif_repo[c]) >= 3
                  and max(motif_repo[c].values()) / len(g) <= 0.5
                  and Counter(r["worth_reviewing"] for r in rows
                              if r["group_id"] in g).get("YES", 0) > len(g) / 2]
        print(f"  STRONG count = {len(strong)}: {strong}")


if __name__ == "__main__":
    main()
