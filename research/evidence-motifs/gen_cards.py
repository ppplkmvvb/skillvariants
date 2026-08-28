"""Generate evidence cards for qualifying motifs from annotated records.

Each card gets: counts, supporting groups with direct SKILL.md URLs and
evidence excerpts, semantic-consistency, cluster-size check. Human-authored
interpretation sections are provided via a CONFIDENCE/WHY map below.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from aggregate import CANONICAL

OUT = Path(__file__).resolve().parent
CARDS = OUT / "motifs"
CARDS.mkdir(exist_ok=True)

# Human-authored interpretation per qualifying motif.
INTERPRETATION = {
    "add-stop-or-escalation-after-repeated-failed-fixes": (
        "Why it may matter: after N failed hypotheses, continuing the loop is the "
        "most common actual failure mode of the debugging skill; multiple teams "
        "independently add an escape valve that preserves the workflow but bounds it.",
        "Confidence: HIGH (9 groups, 9 repos, all worth=YES)."),
    "add-one-hypothesis-at-a-time": (
        "Why it may matter: the counter to shotgun debugging is to change exactly "
        "one variable and falsify it cheaply; this is the single most transferable "
        "engineering practice.",
        "Confidence: MEDIUM (only 4 groups, wording varies, but all preserve the intent)."),
    "add-feedback-loop-rule": (
        "Why it may matter: turns debugging from an investigation into an "
        "instrumentation loop; explicitly names the piece most agents skip.",
        "Confidence: HIGH (4/4 worth=YES)."),
    "add-red-flags-and-anti-pattern-guard": (
        "Why it may matter: making violation of the workflow a named, stoppable "
        "condition lets a recursive agent catch itself mid-mistake.",
        "Confidence: MEDIUM (4 groups but wording is heterogeneous; 2/4 share the "
        "exact Red Flags heading)."),
    "add-routing-boundary-use-case": (
        "Why it may matter: a debugging skill that fires on 'whenever' causes "
        "over-application; explicit use/do-not-use boundaries are a cheap containment "
        "strategy. Note: 3 of these are also 'use-case boundary' variants (Emergency "
        "Stop, Refuse Gate) rather than true routing.",
        "Confidence: MEDIUM (4 groups; cluster share 50% at threshold)."),
    "route-completion-verification-to-separate-skill": (
        "Why it may matter: distinguishing root-cause finding from success-claiming "
        "solves a real verification gap; several repos moved verification to a "
        "separate completion skill explicitly.",
        "Confidence: HIGH (5 groups, 5 repos, 4/5 worth=YES; one supporting group "
        "comes from the common superpowers lineage but is reworded)."),
    "require-reproduction-before-fixing": (
        "Why it may matter: 'never fix what you cannot reproduce' is the canonical "
        "first phase of every debugging methodology; localizing it as a hard rule is "
        "a shared adaptation.",
        "Confidence: HIGH (5/5 first-label, 5 repos)."),
    "restructure-phases-or-named-workflow": (
        "Why it may matter: most teams adapt the four phases to their own pipeline "
        "(Fagan inspection, feedback-loop-first, repro->isolate->identify->fix), "
        "proving the taxonomy is genuinely re-authorized rather than copied.",
        "Confidence: MEDIUM (9 groups but 4 are worth=MAYBE; mostly maintainer-adjacent)."),
    "project-specific-environment-commands": (
        "Why it may matter: the adaptation that most directly turns a generic skill "
        "into an assistant for *this* repo: adding .nix rules, pipx/npx invocations, "
        "Windows/PowerShell handlers. Development ergonomics.",
        "Confidence: MEDIUM (may overlap with workflow restructure; 3/8 worth=YES)."),
    "preserve-root-cause-first-while-compressing": (
        "Why it may matter: a real tradeoff — teams choose brevity over completeness "
        "while keeping the single governing invariant; the 'compressed but not "
        "broken' adaptation is the strongest evidence of deliberate authoring.",
        "Confidence: HIGH (5/5 first-label)."),
    "explicitly-declare-purposes-goals": (
        "Why it may matter: a documentation-led adaptation; makes the skill's "
        "contract explicit to a reading agent before it acts.",
        "Confidence: MEDIUM (3 groups, all worth=PARTIAL)."),
}

TYPE_ORDER = [
    "add-stop-or-escalation-after-repeated-failed-fixes",
    "add-one-hypothesis-at-a-time",
    "add-feedback-loop-rule",
    "add-red-flags-and-anti-pattern-guard",
    "add-routing-boundary-use-case",
    "route-completion-verification-to-separate-skill",
    "require-reproduction-before-fixing",
    "restructure-phases-or-named-workflow",
    "project-specific-environment-commands",
    "preserve-root-cause-first-while-compressing",
    "explicitly-declare-purposes-goals",
]


def slugify(name: str) -> str:
    return name.lower().replace("_", "-")


def main() -> None:
    rows = json.loads((OUT / "group_records_annotated.json").read_text(encoding="utf-8"))
    support: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        for canon in CANONICAL:
            if (r["motif_1"] in CANONICAL[canon]
                    or r["motif_2"] in CANONICAL[canon]
                    or r["motif_3"] in CANONICAL[canon]):
                support[canon].append(r)

    for canon in TYPE_ORDER:
        recs = sorted(support[canon], key=lambda r: r["group_id"])
        if len(recs) < 3:
            continue
        n_repos = len({r["repository"] for r in recs})
        n_occ = sum(r["occurrence_count"] for r in recs)
        first = sum(1 for r in recs if r["motif_1"] in CANONICAL[canon])
        why, conf = INTERPRETATION[canon]
        lines = [
            f"# {canon.replace('-', ' ').title()}",
            "",
            f"Observed across:",
            f"- {len(recs)} distinct mutation groups",
            f"- {n_repos} repositories",
            f"- {n_occ} total occurrences",
            "",
            "## What changed",
            "Structural/behavioral delta extracted from supporting group records:",
            f"- length_delta: "
            + ", ".join(f"{r['length_delta']:+.0%}" for r in recs[:3])
            + " ...",
            f"- headings net added: {sum(r['added_headings'] for r in recs)} vs "
            f"removed: {sum(r['removed_headings'] for r in recs)}",
            f"- semantic-consistency (first-label): {first}/{len(recs)} = "
            f"{first / len(recs):.0%}",
            "",
            why,
            "",
            "## Representative implementations",
            "",
        ]
        for r in recs:
            lines += [
                f"### {r['repository']}/{r['path']}",
                f"Direct SKILL.md URL: {r['direct_skill_url']}",
                f"Added evidence: {r['short_added_excerpt'][:140] or '(none)'}",
                f"Removed evidence: {r['short_removed_excerpt'][:140] or '(none)'}",
            ]
            if r["worth_reviewing"] == "YES":
                lines.append("Manual worth_reviewing: YES")
            lines.append("")
        lines += [
            "## Counterexamples / ambiguity",
            f"- {sum(1 for r in recs if r['motif_1'] not in CANONICAL[canon])} supporting "
            f"groups carry this motif only as a secondary label.",
            "- Some members are plausibly derived from the original superpowers file "
            "rather than independently authored (see depth report §8).",
            "",
            conf,
            "",
        ]
        (CARDS / f"{slugify(canon)}.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"wrote {slugify(canon)}.md ({len(recs)} groups)")


if __name__ == "__main__":
    main()
