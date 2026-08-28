"""Motif consolidation + recurrence aggregation after PASS A annotation.

Normalizes synonymous labels, counts distinct groups/repos/occurrences per
motif, applies the >=3-group & >=3-repo threshold, and flags confounds
(one giant near-copy family, single-repo majority, template propagation).
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent

# Normalized canonical motifs -> expanded synonym set (consolidation rule:
# merge only semantically equivalent concrete changes; keep distinct
# tradeoffs separate, e.g. 'compress phases' vs 'add escalation rule'.
CANONICAL = {
    "add-stop-or-escalation-after-repeated-failed-fixes": [
        "Add escalation rule after 3+ failed fixes",
        "Add The 3-Fix Rule; preserve core principle while compressing",
        "Add stop-after-3-failed-attempts rule",
        "Add Three-fix circuit breaker + red flags as return-to-phase-1",
        "Add The 3-failures rule plus red-flag return to Phase 1",
        "Add stop conditions + 5-step loop; stop after bad guesses",
        "Add Three-Attempt Cap + trigger conditions",
        "Add single-hypothesis test escape clause: 3 failed fixes = framing is wrong",
        "Add 3+ fixes fail escalation handler",
        "Add stop-when-stuck rule",
    ],
    "route-completion-verification-to-separate-skill": [
        "Route completion verification to a separate verification Skill",
        "Route failing-test writing to TDD skill and verification to separate skill",
        "Add dedicated Related Skills heading with 6 cross-skill refs",
        "Add Related Skills heading with cross-skill route",
        "Add explicit Verification phase and Related Skills routing",
    ],
    "require-reproduction-before-fixing": [
        "Require minimal reproducible case; never fix what you cannot reproduce",
        "Start with evidence-not-guesses; minimal repro command rule",
        "Add reproduction gate sign-off + feedback-loop quality criteria",
        "Add reproduce-or-don't-fix rule; unstructured but strong",
        "Split debugging into reproduce/isolate phases with quantitative rate",
    ],
    "preserve-root-cause-first-while-compressing": [
        "Compress into Core-Rule + Workflow + When-stuck; add stop-when-stuck rule",
        "Compress to 4-step flow REPRODUCE/ISOLATE/UNDERSTAND/FIX with one-change-at-a-time rule",
        "Add stop conditions + 5-step loop; stop after bad guesses",
        "Add The 3-Fix Rule; preserve core principle while compressing",
        "Adapt iron law into never-guess and resist-impulse",
    ],
    "add-routing-boundary-use-case": [
        "Add explicit routing boundary: do not use outside debugging",
        "Add Emergency Stop Rule + orientation with use/don't-use boundaries",
        "Add bail-out check before Phase 1",
        "Add slash-command usage wrapper",
        "Add Invocation + Refuse Gate (do not proceed without prerequisites)",
    ],
    "add-one-hypothesis-at-a-time": [
        "Add one-hypothesis-at-a-time + falsify via instrumentation",
        "Add ranked-hypotheses + cheapest-falsification-check rule",
        "Add instrument/photograph-instrument loop before hypothesizing",
        "Rewrite methodology as hypothesis-driven data-flow-traced process",
    ],
    "add-feedback-loop-rule": [
        "Add The Feedback Loop Rule heading",
        "Add Feedback Loop Rule and example-driven guidance (expanded)",
        "Restructure around capture symptom / build feedback loop / reproduce or bound",
        "Add check-the-obvious-first and backward tracing technique",
    ],
    "project-specific-environment-commands": [
        "Add project-specific debugging commands",
        "Add repo-local nix purity rule and route to related skills",
        "Add explicit per-command debugging guidance (npx/pipx)",
        "Add Using-the-Debugger handler (Windows/PowerShell)",
        "Add Debugging Commands section + 4-phase repro/isolate/identify/fix",
        "Given project-specific; preserve iron law",
        "Given project-specific commands",
        "Build as project-specific surfaces + guardrails with workflow",
    ],
    "add-red-flags-and-anti-pattern-guard": [
        "Add violation-indicator red flags",
        "Add red flags returning to Phase 1",
        "Anchor as anti-pattern guard and add escalation rule",
        "Add checklist of anti-patterns + techniques-by-symptom + invariant rules with context-budget note",
        "Add anti-patterns + when-stuck",
        "Add red flags as return-to-phase-1",
    ],
    "restructure-phases-or-named-workflow": [
        "Rename phases to Hypothesis Formation / Minimal Fix / Verification",
        "Restructure to red-flags-stop process with mandatory phase ordering",
        "Replace four phases with observed workflow + Hard Gates + output contract",
        "Reduce to 4 phases each with one focused action",
        "Compact four-phase structure with sparse section removal",
        "Add mandatory-phase-order enforcement marker",
        "Rebuild as disciplined evidence framework with output format + debugging report",
        "Import Fagan Inspection methodology as novel workflow",
        "Rebuild as first-person What-I-Do phases REPRODUCE/ISOLATE/IDENTIFY/FIX",
    ],
    "localize-skill-references": [
        "Swap superpowers:-style skill references to unqualified local references",
        "Explicitly cite lineage as Lifted-from-superpowers and slim",
    ],
    "explicitly-declare-purposes-goals": [
        "Add explicit Purpose section with goals",
        "Add goals / hard rules / read-first structure",
        "Add Key Rules + Tool Use sections",
    ],
    "translate-language-variant": [
        "Translate and restructure to a distinct language variant",
        "Korean-language rebuild; mandatory phases + critical rules",
    ],
}


def main() -> None:
    rows = json.loads((OUT / "group_records_annotated.json").read_text(encoding="utf-8"))

    motif_groups: dict[str, set[int]] = defaultdict(set)
    # motif -> single-repo share tracking
    motif_repo: dict[str, Counter] = defaultdict(Counter)
    motif_occ: Counter = Counter()
    raw_by_group: dict[int, list[str]] = {}

    for record in rows:
        gid = record["group_id"]
        repo = record["repository"]
        labels = [record["motif_1"], record["motif_2"], record["motif_3"]]
        labels = [l for l in labels if l]
        raw_by_group[gid] = labels
        for label in labels:
            for canon, synonyms in CANONICAL.items():
                if label in synonyms:
                    motif_groups[canon].add(gid)
                    motif_repo[canon][repo] += 1
                    motif_occ[canon] += record["occurrence_count"]
                    break

    # apply threshold >=3 groups AND >=3 repos, plus no-single-repo-majority (>50%)
    qualifying = {}
    table = []
    for canon, groups in sorted(motif_groups.items(),
                               key=lambda kv: -len(kv[1])):
        repos = motif_repo[canon]
        n_groups = len(groups)
        n_repos = len(repos)
        n_occ = motif_occ[canon]
        max_repo_share = max(repos.values()) / max(n_groups, 1) if repos else 0
        passes = (
            n_groups >= 3
            and n_repos >= 3
            and max_repo_share <= 0.5
        )
        if passes:
            qualifying[canon] = (n_groups, n_repos, n_occ)
        table.append((canon, n_groups, n_repos, n_occ,
                      f"{max_repo_share:.0%}", "PASS" if passes else "no"))

    out = {"raw_group_labels": {str(k): v for k, v in raw_by_group.items()}}
    print(f"{'motif':58s} groups repos occ  max-share  threshold")
    for canon, g, rr, o, share, stat in table:
        print(f"{canon:58s} {g:4d} {rr:4d} {o:4d}  {share:>8s}  {stat}")
    print(f"\nqualifying motifs: {len(qualifying)}")
    (OUT / "motif_aggregation.json").write_text(
        json.dumps({"qualifying": qualifying, "table": table}, indent=1),
        encoding="utf-8")


if __name__ == "__main__":
    main()
