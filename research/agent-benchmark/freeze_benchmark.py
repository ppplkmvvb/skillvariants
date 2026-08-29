"""Canonicalization audit (spec section 7) + benchmark v1 freeze (section 6).

For every canonical motif from the three family studies, write ONE invariant
sentence and re-check every supporting group against it. Groups that fail the
invariant are rejected (motifs are never merged back to survive recurrence).

Outputs: research/agent-benchmark/v1/canonical-motifs.json + benchmark-manifest.json
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "research" / "agent-benchmark" / "v1"
EM = ROOT / "research" / "evidence-motifs"

# Invariant sentences + per-group re-check decisions from the audit pass.
# supporting = groups that SATISFY the invariant after re-check;
# rejected = previously-affiliated groups that fail it.
AUDIT = {
    # ---- systematic-debugging (11 canonical) ----
    "systematic-debugging": {
        "add-stop-or-escalation-after-repeated-failed-fixes": {
            "invariant": "Introduces an explicit termination, escalation, or reframing trigger tied to a counted number of failed fix attempts.",
            "supporting": [19, 25, 31, 33, 43, 45, 56, 58, 67], "rejected": [],
        },
        "restructure-phases-or-named-workflow": {
            "invariant": "Renames, reorders, or replaces the named phase structure of the methodology while preserving the same overall root-cause method. (broad)",
            "supporting": [21, 25, 28, 30, 32, 33, 38, 39, 48], "rejected": [],
        },
        "project-specific-environment-commands": {
            "invariant": "Adds commands, configuration, or environment checks specific to a particular repository, stack, or deployment context.",
            "supporting": [3, 15, 17, 20, 24, 31, 66, 76], "rejected": [],
        },
        "route-completion-verification-to-separate-skill": {
            "invariant": "Delegates final completion/verification checking to another named skill or a separate verification step instead of doing it inline.",
            "supporting": [2, 11, 17, 28, 41], "rejected": [],
        },
        "require-reproduction-before-fixing": {
            "invariant": "Makes producing a reproduction (or explicit handling of non-reproducibility) a required, gated step before any fix.",
            "supporting": [4, 38, 55, 61, 69], "rejected": [],
        },
        "preserve-root-cause-first-while-compressing": {
            "invariant": "Substantially shortens the document while explicitly retaining the root-cause-first governing rule.",
            "supporting": [43, 53, 58, 62, 55], "rejected": [],
        },
        "add-one-hypothesis-at-a-time": {
            "invariant": "Requires forming and testing exactly one hypothesis (or one change) at a time, with explicit falsification or instrumentation.",
            "supporting": [5, 63, 72, 83], "rejected": [],
        },
        "add-red-flags-and-anti-pattern-guard": {
            "invariant": "Adds an explicit list of violation indicators or anti-patterns that signal the process itself is being violated.",
            "supporting": [5, 19, 36, 68], "rejected": [],
        },
        "add-routing-boundary-use-case": {
            "invariant": "Adds explicit boundaries declaring when the skill must not be used or when it must hand off.",
            "supporting": [8, 26, 41, 54], "rejected": [],
        },
        "add-feedback-loop-rule": {
            "invariant": "Elevates building/validating a feedback loop (reproduction plus instrumentation) into a named, mandatory rule.",
            "supporting": [20, 22, 32], "rejected": [33],
        },
        "explicitly-declare-purposes-goals": {
            "invariant": "Adds an explicit purpose/goals statement near the top defining what the skill achieves.",
            "supporting": [29, 49, 74], "rejected": [],
        },
    },
    # ---- frontend-design (4 recurring canonical) ----
    "frontend-design": {
        "add-framework-specific-design-rules": {
            "invariant": "Adds design/implementation rules tied to a specific UI framework, stack, or design-token system.",
            "supporting": [13, 17, 26, 29, 57], "rejected": [],
        },
        "add-evaluation-or-review-gate": {
            "invariant": "Adds an explicit evaluation, review, or verification step/gate that work must pass before delivery.",
            "supporting": [15, 48, 58, 62, 40], "rejected": [],
        },
        "add-contract-scope-or-output-gates": {
            "invariant": "Defines an explicit contract for when the skill applies and what it produces (scope/trigger/guardrails/output format) in place of free-form work.",
            "supporting": [8, 36, 49, 52], "rejected": [41, 54],
        },
        "add-project-specific-rules": {
            "invariant": "Adds design rules grounded in this specific repository or product (its stack, files, or design language).",
            "supporting": [10, 20, 23], "rejected": [],
        },
    },
    # ---- brainstorming (8 candidate canonical -> audit result) ----
    "brainstorming": {
        "add-explicit-hard-gate-implementation-lock": {
            "invariant": "Adds an explicit, unavoidable prohibition on writing code or taking implementation action before the design is approved.",
            "supporting": [29, 30, 44, 50, 60, 82], "rejected": [],
        },
        "add-ownership-or-handoff-boundary": {
            "invariant": "States what this skill owns versus what it delegates, or defines an explicit handoff boundary to another skill or pipeline stage.",
            "supporting": [12, 20, 25, 46, 76, 51], "rejected": [],
        },
        "add-questioning-or-interaction-protocol": {
            "invariant": "Prescribes a concrete questioning/interaction protocol (one question at a time, tool usage, or question-count rules). (broad)",
            "supporting": [36, 37, 41, 62, 69, 79, 27], "rejected": [],
        },
        "add-diverge-converge-phase-split": {
            "invariant": "Structures the process as an explicit divergent-exploration phase followed by a convergent decision/presentation phase.",
            "supporting": [6, 28, 49, 80], "rejected": [],
        },
        "add-greenfield-vs-existing-path-split": {
            "invariant": "Adds a distinct path for greenfield work versus existing-codebase work.",
            "supporting": [9, 15, 21], "rejected": [],
        },
        "add-traceability-or-spec-output-rule": {
            "invariant": "Mandates a specific spec/artifact output structure or a traceability requirement the design must satisfy.",
            "supporting": [32, 34], "rejected": [17, 57],
        },
        "add-environment-or-availability-guard": {
            "invariant": "Gates the skill's availability on an environment or workflow-state condition.",
            "supporting": [1, 10], "rejected": [26],
        },
        "add-stop-or-fallback-condition": {
            "invariant": "Adds explicit stop conditions or fallback behavior for when the process stalls or its assumptions fail.",
            "supporting": [35, 54], "rejected": [72],
        },
    },
}

DISPLAY = {
    "add-stop-or-escalation-after-repeated-failed-fixes": "Add stop or escalation after repeated failed fixes",
    "restructure-phases-or-named-workflow": "Restructure phases or named workflow",
    "project-specific-environment-commands": "Add project-specific environment commands",
    "route-completion-verification-to-separate-skill": "Route completion verification to a separate skill",
    "require-reproduction-before-fixing": "Require reproduction before fixing",
    "preserve-root-cause-first-while-compressing": "Preserve root-cause-first while compressing",
    "add-one-hypothesis-at-a-time": "Add one-hypothesis-at-a-time",
    "add-red-flags-and-anti-pattern-guard": "Add red-flags and anti-pattern guard",
    "add-routing-boundary-use-case": "Add routing-boundary use-case",
    "add-feedback-loop-rule": "Add feedback-loop rule",
    "explicitly-declare-purposes-goals": "Explicitly declare purposes/goals",
    "add-framework-specific-design-rules": "Add framework-specific design rules",
    "add-evaluation-or-review-gate": "Add evaluation-or-review gate",
    "add-contract-scope-or-output-gates": "Add contract/scope/output gates",
    "add-project-specific-rules": "Add project-specific rules",
    "add-explicit-hard-gate-implementation-lock": "Add explicit hard-gate implementation lock",
    "add-ownership-or-handoff-boundary": "Add ownership-or-handoff boundary",
    "add-questioning-or-interaction-protocol": "Add questioning-or-interaction protocol",
    "add-diverge-converge-phase-split": "Add diverge/converge phase split",
    "add-greenfield-vs-existing-path-split": "Add greenfield-vs-existing path split",
    "add-traceability-or-spec-output-rule": "Add traceability-or-spec-output rule",
    "add-environment-or-availability-guard": "Add environment-or-availability guard",
    "add-stop-or-fallback-condition": "Add stop-or-fallback condition",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    canonical = []
    for family, motifs in AUDIT.items():
        for label, audit in motifs.items():
            n_groups = len(audit["supporting"])
            repos_field = "n_repos"  # computed later by aggregation script
            canonical.append({
                "family": family,
                "label": label,
                "display_name": DISPLAY[label],
                "invariant": audit["invariant"],
                "supporting_groups": audit["supporting"],
                "rejected_groups": audit["rejected"],
                "group_count": n_groups,
            })
    (OUT / "canonical-motifs.json").write_text(
        json.dumps({"audit_note": "one invariant per motif; supporting groups re-checked; "
                                 "rejected groups listed; no merging back to survive recurrence",
                    "canonical_motifs": canonical},
                   indent=1, ensure_ascii=False), encoding="utf-8")

    # freeze benchmark manifest: groups from the three annotated family files
    family_files = {
        "systematic-debugging": EM / "group_records_annotated.json",
        "frontend-design": EM / "frontend-design" / "frontend-design-group-records-annotated.json",
        "brainstorming": EM / "brainstorming" / "brainstorming-group-records-annotated.json",
    }
    groups_out = []
    for family, path in family_files.items():
        rows = json.loads(path.read_text(encoding="utf-8"))
        by_label = {m["label"]: m for m in canonical if m["family"] == family}
        for r in rows:
            gid = r["group_id"]
            canon_members = []
            for label, audit in AUDIT[family].items():
                if gid in audit["supporting"]:
                    canon_members.append(label)
            groups_out.append({
                "family": family,
                "group_id": gid,
                "repository": r["repository"],
                "path": r["path"],
                "ref": r.get("ref", ""),
                "direct_skill_url": r["direct_skill_url"],
                "archetype": r["archetype"],
                "human_meaningful": r["meaningful_behavior_change"],
                "human_worth_reviewing": r["worth_reviewing"],
                "human_motif_labels": [x for x in (r.get("motif_1"), r.get("motif_2"), r.get("motif_3")) if x],
                "canonical_motifs": canon_members,
                "added_excerpt": r.get("short_added_excerpt", ""),
                "removed_excerpt": r.get("short_removed_excerpt", ""),
            })
    manifest = {
        "benchmark_version": "v1",
        "frozen_at": str(date.today()),
        "frozen_by": "human PASS A coding pass (three family studies), then canonicalization audit",
        "worth_reviewing_note": "research metadata only; NOT ground truth for product recommendations",
        "counts": {
            "groups": len(groups_out),
            "canonical_motifs": len(canonical),
            "recurring_canonical_motifs": sum(1 for c in canonical if c["group_count"] >= 3),
        },
        "canonical_motifs": canonical,
        "groups": groups_out,
    }
    (OUT / "benchmark-manifest.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    print("frozen groups:", len(groups_out))
    print("canonical motifs:", len(canonical),
          "recurring(>=3):", sum(1 for c in canonical if c["group_count"] >= 3))
    print("audit rejections:",
          {f: sum(len(a["rejected"]) for a in m.values()) for f, m in AUDIT.items()})
    print("per-family canonical:",
          dict(Counter(c["family"] for c in canonical)))


if __name__ == "__main__":
    main()
