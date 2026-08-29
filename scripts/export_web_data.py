"""Deterministic Web data exporter (spec sections 11, 20).

Reads the runtime study artifacts for the three launch families and emits
web/data/<family>.json with summary, accepted motifs (invariant, signature,
counts, interpretation, tradeoff, representative implementations with exact
source URLs), and precomputed compare payloads for the first representatives.

Counts and URLs come from artifacts only; interpretation/tradeoff text comes
from the frozen family studies. Never hand-entered in UI code.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

RUNTIME = ROOT / "research" / "runtime-v0.2"
OUT = ROOT / "web" / "data"
OUT.mkdir(parents=True, exist_ok=True)

CAPTURE_NOTE = ("Counts captured 2026-08-29 from GitHub Code Search; "
                "GitHub results change over time.")

# Interpretation/tradeoff text from the frozen family studies (human-audited).
NARRATIVE = {
    "systematic-debugging": {
        "add-stop-or-escalation-after-repeated-failed-fixes": (
            "An explicit trigger (usually three failed fix attempts) stops or escalates the debugging loop.",
            "May bound an unbounded investigation loop so the agent reports back instead of thrashing.",
            "A premature stop can cut off hard-but-solvable investigations."),
        "route-completion-verification-to-separate-skill": (
            "Final completion/verification is delegated to a named verification skill instead of inline.",
            "May separate root-cause finding from success-claiming.",
            "Adds a dependency on the verification skill being available."),
        "require-reproduction-before-fixing": (
            "Producing a reproduction becomes a gated step before any fix.",
            "Fixes without reproduction are a common source of wasted effort.",
            "Some bugs are expensive to reproduce."),
        "add-project-or-product-specific-design-rules": (
            "Adds commands, configuration, or environment checks specific to one repository or stack.",
            "Grounds the generic method in the actual repository tooling.",
            "Reduces portability of the skill."),
        "add-red-flags-and-anti-pattern-guard": (
            "Adds explicit violation indicators or anti-pattern lists.",
            "Lets a recursive agent catch itself mid-violation.",
            "Lists can go stale as the method evolves."),
        "add-feedback-loop-rule": (
            "Elevates building/validating a feedback loop into a named, mandatory rule.",
            "Names the step most agents skip: instrumenting before hypothesizing.",
            "Instrumentation adds upfront cost."),
        "preserve-root-cause-first-while-compressing": (
            "Substantially shortens the document while explicitly retaining the root-cause-first rule.",
            "A deliberate brevity-without-losing-the-invariant tradeoff.",
            "Compressed variants lose supporting techniques."),
        "replace-with-named-methodology": (
            "Replaces the four-phase method with a different named methodology or framing.",
            "Shows the taxonomy being genuinely re-authored rather than copied.",
            "New methods may lose the original's guarantees."),
    },
    "frontend-design": {
        "add-framework-specific-design-rules": (
            "Adds rules tied to a concrete UI stack (shadcn/ui, React/Next.js, Tailwind tokens, stack priority).",
            "Generic aesthetic guidance may not survive contact with a real component library.",
            "Couples the skill to a stack version."),
        "add-evaluation-or-review-gate": (
            "Adds an explicit review/verification gate that output must pass before delivery.",
            "Generated UI is rarely reviewed against intent without a forced pass.",
            "Checklists can become boilerplate."),
        "add-contract-scope-or-output-gates": (
            "Defines when the skill applies and what it must produce (triggers, output contracts, DESIGN.md).",
            "Prevents drift into generic implementation work.",
            "Contracts add upfront friction."),
        "add-project-specific-rules": (
            "Grounds rules in this repo's design language, context files, or platform quirks.",
            "Adapts a generic skill into a project design system.",
            "Not reusable outside the project."),
    },
    "brainstorming": {
        "add-explicit-hard-gate-implementation-lock": (
            "An unavoidable prohibition on writing code before the design is approved.",
            "The most common failure is skipping ideation entirely.",
            "Rigid gates can block genuinely trivial changes."),
        "add-ownership-or-handoff-boundary": (
            "States what the skill owns vs delegates, or where it hands off next.",
            "Multi-skill pipelines need clear stage boundaries.",
            "Requires the downstream stage to exist."),
        "add-questioning-or-interaction-protocol": (
            "Prescribes concrete questioning behavior (one question at a time, tool usage, question counts).",
            "Unstructured questioning degenerates into interrogation or guesswork.",
            "Protocol can feel mechanical to users."),
        "add-diverge-converge-phase-split": (
            "Explicit divergent exploration followed by convergent presentation.",
            "Prevents premature commitment to the first idea.",
            "Longer process for small decisions."),
        "add-greenfield-vs-existing-path-split": (
            "Distinct paths for new projects versus established codebases.",
            "Context exploration differs fundamentally between the two.",
            "More branches to maintain."),
        "add-stop-or-fallback-condition": (
            "Stop conditions or fallback behavior when the process stalls.",
            "Same escape-hatch family as the debugging skill's stop rules.",
            "Fallbacks can hide process bugs."),
    },
}


def run_compare(target_url: str, variant_url: str) -> dict | None:
    """Deterministic compare payload via internal API (cached fetches)."""
    import difflib
    from skillvariants.cli import _load_doc
    from skillvariants.classify import classify_pair, mutation_summary
    from skillvariants.features import extract_features
    from skillvariants.github import GitHubClient, GitHubError
    from skillvariants.similarity import score_similarity
    try:
        client = GitHubClient(cache_dir=ROOT / ".cache" / "skillvariants")
        ref_a, doc_a, feats_a = _load_doc(client, target_url)
        ref_b, doc_b, feats_b = _load_doc(client, variant_url)
    except (ValueError, GitHubError, Exception):
        return None
    sim = score_similarity(doc_a, feats_a, doc_b, feats_b)
    classification = classify_pair(doc_a, feats_a, doc_b, feats_b, sim)
    summary = mutation_summary(doc_a, feats_a, doc_b, feats_b, sim, classification)
    diff = list(difflib.unified_diff(
        doc_a.body.splitlines(), doc_b.body.splitlines(),
        fromfile="target", tofile="variant", lineterm="", n=1))
    brief = [ln[:160] for ln in diff
             if ln.startswith(("+", "-")) and not ln.startswith(("+++", "---"))][:24]
    return {
        "similarity": sim.as_dict(),
        "length_change": summary["length_change"],
        "workflow_headings": summary["workflow_headings"],
        "detected_mutation": classification.primary,
        "text_diff_brief": brief,
    }


def main() -> None:
    for family in ("systematic-debugging", "frontend-design", "brainstorming"):
        study_dir = RUNTIME / family
        manifest = json.loads((study_dir / "manifest.json").read_text(encoding="utf-8"))
        motifs = json.loads((study_dir / "motifs.json").read_text(encoding="utf-8"))
        narrative = NARRATIVE[family]
        target_url = manifest["target"]["direct_skill_url"]

        accepted = []
        for motif in motifs["accepted"]:
            key = motif["label"]
            what, why, tradeoff = narrative.get(key, (
                motif["invariant"],
                "Documented in the family study.",
                "Documented in the family study."))
            reps = []
            for g in motif["supporting_groups"][:3]:
                variant_url = g["direct_skill_url"]
                compare = run_compare(target_url, variant_url)
                reps.append({
                    "repository": g["repository"],
                    "path": g["path"],
                    "ref": g.get("ref", ""),
                    "direct_skill_url": variant_url,
                    "compare": compare,
                    # GitHub results change over time: a ref/file can vanish
                    # after capture. The compare is then unavailable.
                    "source_available": compare is not None,
                })
            accepted.append({
                "label": motif["label"],
                "display_name": motif["display_name"],
                "invariant": motif["invariant"],
                "behavior_signature": motif["behavior_signature"],
                "group_count": motif["group_count"],
                "repository_count": motif["repository_count"],
                "what_changed": what,
                "interpretation": why,
                "tradeoff": tradeoff,
                "representatives": reps,
            })
        payload = {
            "schema_version": "1",
            "family": family,
            "capture_note": CAPTURE_NOTE,
            "target": manifest["target"],
            "summary": {
                "groups_total": manifest["counts"]["groups_total"],
                "groups_analyzed": manifest["counts"]["groups_analyzed"],
                "exact_copy_count": manifest["counts"].get("exact_copy_count", 0),
                "accepted_motif_count": len(accepted),
            },
            "accepted_motifs": accepted,
        }
        out = OUT / f"{family}.json"
        out.write_text(json.dumps(payload, indent=1, ensure_ascii=False),
                       encoding="utf-8")
        print(f"wrote {out.name}: motifs={len(accepted)} "
              f"compares={sum(1 for m in accepted for r in m['representatives'] if r['compare'])}")


if __name__ == "__main__":
    main()
