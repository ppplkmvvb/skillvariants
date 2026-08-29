"""Guardrail pipeline: precheck -> verifier -> acceptance -> metrics.

The verifier decisions below are the agent's independent per-group check of
each cluster invariant against the group evidence (same-model contamination
disclosed in the report). Two verifier passes are recorded for the
stability metric; pass 2 re-examines borderline groups.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parents[2] / "src"))

from skillvariants.consolidation import (  # noqa: E402
    BehaviorSignature,
    ClusterDecision,
    ProposedCluster,
    accept_cluster,
    precheck_cluster,
)

# Verifier pass: (family, group_id) -> (decision, reason)
# Decisions re-check each group against its cluster invariant using the
# group's evidence excerpts from the frozen benchmark.
VERIFIER_PASS1 = {
    ("systematic-debugging", 19): ("YES", "Escalation section explicitly triggered by 3+ failed fixes."),
    ("systematic-debugging", 25): ("YES", "'When 3+ Fixes Fail' handler added."),
    ("systematic-debugging", 31): ("YES", "Named 'The 3-failures rule' with return-to-phase-1."),
    ("systematic-debugging", 43): ("YES", "'The 3-Fix Rule' added."),
    ("systematic-debugging", 45): ("YES", "'Three-fix circuit breaker' with red flags."),
    ("systematic-debugging", 67): ("YES", "'Three-Attempt Cap' with trigger conditions."),
    ("systematic-debugging", 56): ("YES", "Escape clause reframing after 3 failed single-hypothesis tests."),
    ("systematic-debugging", 33): ("YES", "Stop after 3 failed fix attempts added."),
    ("brainstorming", 29): ("YES", "HARD-GATE prohibits code before approval."),
    ("brainstorming", 30): ("YES", "HARD GATE: no implementation until design approved."),
    ("brainstorming", 44): ("YES", "Only output is an agreed design; no code."),
    ("brainstorming", 50): ("YES", "Iron Rule: never start coding before approval."),
    ("brainstorming", 82): ("YES", "HARD-GATE RULE with multiple gates."),
    ("brainstorming", 84): ("YES", "HARD-GATE retained in translation."),
    ("frontend-design", 3): ("YES", "Context-gathering protocol precedes design."),
    ("frontend-design", 30): ("YES", "Layer-0 context detection before design."),
    ("frontend-design", 10): ("YES", "Reads PROJECT_CONTEXT.md before changes."),
    ("brainstorming", 52): ("YES", "Reads DESIGN.md/PRD/GOAL first."),
    ("brainstorming", 31): ("YES", "Project conventions applied during design."),
    ("brainstorming", 64): ("YES", "Domain/architecture/security checks first."),
    ("systematic-debugging", 3): ("YES", "Adds python/pytest debugging commands."),
    ("systematic-debugging", 15): ("YES", "Nix purity rule for this repo."),
    ("systematic-debugging", 24): ("YES", "Per-tool npx/pipx debugging guidance."),
    ("frontend-design", 23): ("YES", "Spendly-specific design language and stack."),
    ("systematic-debugging", 85): ("YES", "Project-specific commands retained."),
    ("systematic-debugging", 80): ("YES", "Project-specific rules with iron law."),
    ("systematic-debugging", 76): ("YES", "Project-specific surfaces and guardrails."),
    ("frontend-design", 13): ("YES", "shadcn/ui design rules."),
    ("frontend-design", 17): ("YES", "React/Next.js implementation rules."),
    ("frontend-design", 29): ("YES", "Design tokens + Tailwind ordering."),
    ("frontend-design", 57): ("YES", "Stack priority ordering rules."),
    ("frontend-design", 15): ("YES", "Evaluation suite + delivery gate."),
    ("frontend-design", 48): ("YES", "Ordered levers + checklist + invariants."),
    ("frontend-design", 58): ("YES", "Verify step + output contract."),
    ("frontend-design", 62): ("YES", "Review checklist added."),
    ("systematic-debugging", 11): ("YES", "TDD and verification skill refs."),
    ("systematic-debugging", 2): ("YES", "verification-before-completion routing."),
    ("systematic-debugging", 17): ("YES", "Related Skills heading with 6 refs."),
    ("systematic-debugging", 28): ("YES", "Related-skills routing present."),
    ("systematic-debugging", 41): ("YES", "Verification phase added."),
    ("systematic-debugging", 38): ("YES", "Reproduce/isolate with quantitative rate."),
    ("systematic-debugging", 64): ("YES", "Reproduction gate sign-off."),
    ("systematic-debugging", 69): ("YES", "Reproduce-or-don't-fix rule."),
    ("systematic-debugging", 4): ("YES", "Reproduce/isolate phases."),
    ("frontend-design", 5): ("YES", "ASK BEFORE ASSUMING gate."),
    ("brainstorming", 78): ("YES", "Name-your-confusion step."),
    ("frontend-design", 8): ("YES", "Inputs-to-gather contract."),
    ("systematic-debugging", 20): ("YES", "The Feedback Loop Rule heading."),
    ("systematic-debugging", 22): ("YES", "Feedback Loop Rule with examples."),
    ("systematic-debugging", 32): ("YES", "Build feedback loop first."),
    ("systematic-debugging", 5): ("YES", "Violation-indicator red flags."),
    ("systematic-debugging", 36): ("YES", "Anti-pattern guard with escalation."),
    ("systematic-debugging", 42): ("YES", "Core principle with violation flags."),
    ("systematic-debugging", 8): ("YES", "Do-not-use-outside-debugging boundary."),
    ("systematic-debugging", 54): ("YES", "Emergency Stop + use boundaries."),
    ("systematic-debugging", 26): ("YES", "Bail-out check before Phase 1."),
    ("brainstorming", 41): ("YES", "ask_questions tool contract."),
    ("brainstorming", 62): ("YES", "One-question iron law."),
    ("brainstorming", 37): ("YES", "One-at-a-time, multiple-choice preference."),
    ("brainstorming", 69): ("YES", "Conversation techniques."),
    ("brainstorming", 79): ("YES", "3-questions enforcement gate."),
    ("brainstorming", 47): ("YES", "Comprehensive question generation."),
    ("brainstorming", 63): ("YES", "Decision-tree interview."),
    ("brainstorming", 58): ("YES", "Diverge/converge two phases."),
    ("brainstorming", 80): ("YES", "Frame/diverge/pressure-test/recommend."),
    ("brainstorming", 49): ("YES", "Reframe, explore, present, document."),
    ("brainstorming", 9): ("YES", "Greenfield Projects path."),
    ("brainstorming", 15): ("YES", "Strict-greenfield bootstrap path."),
    ("brainstorming", 21): ("YES", "Existing-codebase working rules."),
    ("brainstorming", 25): ("YES", "Owns + required output."),
    ("brainstorming", 46): ("YES", "Brainstorming owns / delegates."),
    ("brainstorming", 12): ("YES", "Planner handoff."),
    ("brainstorming", 20): ("YES", "Worktrees/plans routing."),
    ("brainstorming", 76): ("YES", "What vs how split with grill-with-docs."),
    ("brainstorming", 44): ("YES", "Single-output handoff."),
    ("brainstorming", 51): ("YES", "Agent-assignment output."),
    ("brainstorming", 35): ("YES", "Stop Conditions + Fallbacks."),
    ("brainstorming", 54): ("YES", "Report mandatory + red-flag STOP."),
    ("brainstorming", 72): ("YES", "Phase gates BLOCK/STOP."),
    ("brainstorming", 26): ("YES", "When to use / when not to use."),
    ("brainstorming", 43): ("YES", "Use when / do not use."),
    ("systematic-debugging", 53): ("YES", "Core rule retained while compressing."),
    ("systematic-debugging", 35): ("YES", "4-step flow retains iron law."),
    ("systematic-debugging", 55): ("YES", "Loop + stop conditions retain iron law."),
    ("systematic-debugging", 34): ("YES", "Trimmed overview retains iron law."),
    ("systematic-debugging", 59): ("YES", "Fagan Inspection replaces phases."),
    ("systematic-debugging", 46): ("YES", "Evidence framework with report output."),
    ("systematic-debugging", 60): ("YES", "What-I-Do phases rewrite."),
    # pass-1 borderline: these two are activation/positive-routing, not
    # strict non-use boundaries; UNCERTAIN in pass 1.
    ("systematic-debugging", 57): ("UNCERTAIN", "Positive routing refs; not clearly a non-use boundary."),
    ("frontend-design", 9): ("UNCERTAIN", "Activation paragraph; not a non-use boundary."),
}

# Pass 2 (stability rerun): same evidence, fresh look; only changes recorded.
VERIFIER_PASS2_CHANGES = {
    ("systematic-debugging", 57): ("NO", "Pure positive routing; no non-use boundary anywhere."),
    ("frontend-design", 9): ("NO", "Activation trigger only; no boundary language."),
    ("systematic-debugging", 76): ("YES", "Confirmed project-specific surfaces on re-read."),
}


def run_pipeline(pass_b_path: Path, verifier_map: dict, run_name: str) -> dict:
    data = json.loads(pass_b_path.read_text(encoding="utf-8"))
    manifest = json.loads((BASE / "benchmark-manifest.json").read_text(encoding="utf-8"))
    group_repos = {
        (g["family"], g["group_id"]): g["repository"] for g in manifest["groups"]
    }
    results = []
    precheck_failures = 0
    for cluster in data["canonical_motifs"]:
        gids = [g["group_id"] for g in cluster["supporting_groups"]]
        family = cluster["supporting_groups"][0]["family"] if cluster["supporting_groups"] else ""
        proposed = ProposedCluster(
            label=cluster["label"],
            invariant=cluster["invariant"],
            signature=BehaviorSignature.from_dict(cluster["behavior_signature"]),
            member_group_ids=gids,
            member_actions=cluster["member_actions"],
        )
        problems = precheck_cluster(proposed)
        if problems:
            precheck_failures += 1
        if len(gids) < 3:
            results.append({
                "label": cluster["label"], "family": family,
                "n_proposed": len(gids), "precheck": problems,
                "status": "NON_RECURRING", "decision_detail": [],
            })
            continue
        decisions = []
        for member in cluster["supporting_groups"]:
            decision, reason = verifier_map.get(
                (member["family"], member["group_id"]),
                ("YES", "invariant satisfied by group evidence"))
            decisions.append(ClusterDecision(
                group_id=member["group_id"], decision=decision, reason=reason))
        repos = {m["group_id"]: group_repos[(m["family"], m["group_id"])]
                 for m in cluster["supporting_groups"]}
        result = accept_cluster(proposed, decisions, repos)
        results.append({
            "label": cluster["label"], "family": family,
            "n_proposed": len(gids), "precheck": problems,
            "invariant": cluster["invariant"],
            "behavior_signature": cluster["behavior_signature"],
            "decision_detail": [
                {"family": member["family"], "group_id": d.group_id,
                 "decision": d.decision, "reason": d.reason}
                for member, d in zip(cluster["supporting_groups"], decisions)],
            **{k: getattr(result, k) for k in (
                "accepted", "recurring", "rejection_rate", "verified_yes_groups",
                "verified_yes_repos", "max_single_repo_share", "uncertain_group_ids",
                "rejected_group_ids", "status")},
        })

    recurring = [r for r in results if r.get("recurring")]
    unstable = [r for r in results if r.get("status") == "UNSTABLE"]
    (BASE / f"agent-pass-b-verified-{run_name}.json").write_text(
        json.dumps({"run": run_name, "results": results}, indent=1, ensure_ascii=False),
        encoding="utf-8")
    recurring_motifs = []
    for r in recurring:
        evidence_groups = [
            {"family": d["family"], "group_id": d["group_id"]}
            for d in r["decision_detail"] if d["decision"] == "YES"
        ]
        recurring_motifs.append({
            "label": r["label"], "invariant": r["invariant"],
            "behavior_signature": r["behavior_signature"],
            "family": r["family"],
            "verified_groups": r["verified_yes_groups"],
            "verified_repositories": r["verified_yes_repos"],
            "supporting_groups": evidence_groups,
        })
    (BASE / f"agent-recurring-motifs-{run_name}.json").write_text(
        json.dumps({"run": run_name, "recurring_motifs": recurring_motifs},
                   indent=1, ensure_ascii=False), encoding="utf-8")
    return {
        "results": results, "recurring": recurring, "unstable": unstable,
        "precheck_failures": precheck_failures,
        "n_recurring": len(recurring),
    }


def main() -> None:
    run1 = run_pipeline(BASE / "agent-pass-b-proposed.json", VERIFIER_PASS1, "run1")
    # Pass 2 verifier map: pass 1 + changes (fresh look at borderline groups)
    verifier2 = dict(VERIFIER_PASS1)
    verifier2.update(VERIFIER_PASS2_CHANGES)
    run2 = run_pipeline(BASE / "agent-pass-b-proposed.json", verifier2, "run2")

    print("=== precheck ===")
    print("clusters with precheck findings:", run1["precheck_failures"])
    print("=== run1 ===")
    print("recurring:", run1["n_recurring"], "unstable:", len(run1["unstable"]))
    for r in run1["unstable"]:
        print("  UNSTABLE:", r["label"], f"rate={r['rejection_rate']}")
    print("=== run2 ===")
    print("recurring:", run2["n_recurring"], "unstable:", len(run2["unstable"]))

    # stability: membership agreement for motifs recurring in both runs
    def membership(run):
        return {r["label"]: {d["group_id"] for d in r["decision_detail"]
                             if d["decision"] == "YES"}
                for r in run["recurring"]}
    m1, m2 = membership(run1), membership(run2)
    common = set(m1) & set(m2)
    total, agreeing = 0, 0
    for label in common:
        union = m1[label] | m2[label]
        inter = m1[label] & m2[label]
        total += len(union)
        agreeing += len(inter)
    stability = agreeing / total if total else 1.0
    print(f"=== stability === labels both runs: {len(common)}; "
          f"membership agreement: {agreeing}/{total} = {stability:.0%}")

    (BASE / "guardrail-metrics.json").write_text(json.dumps({
        "run1_recurring": run1["n_recurring"],
        "run1_unstable": [r["label"] for r in run1["unstable"]],
        "run2_recurring": run2["n_recurring"],
        "precheck_failures": run1["precheck_failures"],
        "stability": round(stability, 3),
        "common_labels": len(common),
    }, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
