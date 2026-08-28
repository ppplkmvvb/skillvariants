"""PASS B: for the qualifying motifs, check whether existing deterministic
features can recover them (YES/PARTIAL/NO) and compute exploratory
precision/recall of small generic phrase detectors on annotated groups.

No embeddings, no LLM, no new product code — research only.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent

# Existing feature coverage map for each qualifying motif.
# category: EXISTING (directly available in features), PARTIAL (needs a small
# generic phrase/heading detector), NO (would need new signal design).
FEATURE_COVERAGE = {
    "add-stop-or-escalation-after-repeated-failed-fixes": ("PARTIAL", "heading turnover + phrase detector"),
    "add-one-hypothesis-at-a-time": ("PARTIAL", "heading/phrase detector"),
    "add-feedback-loop-rule": ("EXISTING", "heading-name match (feedback loop)"),
    "add-red-flags-and-anti-pattern-guard": ("EXISTING", "heading-name match (red flags / anti-pattern)"),
    "add-routing-boundary-use-case": ("EXISTING", "routing boundary phrases"),
    "route-completion-verification-to-separate-skill": ("EXISTING", "cross-skill ref delta + routing signals"),
    "require-reproduction-before-fixing": ("PARTIAL", "reproduction phrase detector"),
    "restructure-phases-or-named-workflow": ("PARTIAL", "heading turnover + phase-name diff"),
    "project-specific-environment-commands": ("EXISTING", "command delta + project phrase regex"),
    "preserve-root-cause-first-while-compressing": ("EXISTING", "ALL-CAPS rule preservation + length delta"),
    "explicitly-declare-purposes-goals": ("EXISTING", "heading-name match (purpose/goals)"),
}

# Small generic phrase detectors, one per motif with PARTIAL/EXISTING.
# Returns True if the group's representative body/features fire.
def det_stop(body: str, headings: list[str]) -> bool:
    return bool(
        re.search(r"(3|three)\s*(failed|fix|hypothes)", body, re.I)
        or re.search(r"(stop|circuit breaker|escalat)", body, re.I)
        or any("3-failures" in h.lower() or "stop" in h.lower()
               or "escalation" in h.lower() for h in headings)
    )


def det_one_hypothesis(body: str) -> bool:
    return bool(re.search(r"(one|single)\s*(hypothes|change at a time)", body, re.I)
                or re.search(r"falsif", body, re.I))


def det_feedback_loop(headings: list[str]) -> bool:
    return any("feedback loop" in h.lower() for h in headings)


def det_red_flags(headings: list[str]) -> bool:
    return any("red flag" in h.lower() or "anti-pattern" in h.lower()
               or "violation" in h.lower() for h in headings)


def det_route_boundary(rep) -> bool:
    return bool(rep.feats.routing_signals)


def det_route_verification(rep) -> bool:
    return (
        "verification" in (rep.doc.description or "").lower()
        or any("verification" in r.lower() for r in rep.feats.cross_skill_refs)
        or any("verification" in s.lower() for s in rep.feats.routing_signals)
    )


def det_reproduce(body: str) -> bool:
    return bool(re.search(r"(reproduc|repro)", body, re.I))


def det_restructure(headings: list[str], turnover: int) -> bool:
    return turnover >= 3


def det_project_cmds(rep) -> bool:
    return bool(rep.feats.commands) and any(
        p in (rep.doc.description or "") for p in ("project", "repo", "specific"))


def det_preserve_root_cause(rep) -> bool:
    body = rep.doc.body
    return bool(re.search(r"root cause", body, re.I)) or bool(
        any("root cause" in r.lower() for r in rep.magnitude_signals))


def det_purpose_goals(headings: list[str]) -> bool:
    return any(h.lower() in ("purpose", "goals", "what i do") for h in headings)


DETECTORS = {
    "add-stop-or-escalation-after-repeated-failed-fixes": (det_stop, "body+headers"),
    "add-one-hypothesis-at-a-time": (det_one_hypothesis, "body"),
    "add-feedback-loop-rule": (det_feedback_loop, "headings"),
    "add-red-flags-and-anti-pattern-guard": (det_red_flags, "headings"),
    "add-routing-boundary-use-case": (det_route_boundary, "features"),
    "route-completion-verification-to-separate-skill": (det_route_verification, "features"),
    "require-reproduction-before-fixing": (det_reproduce, "body"),
    "restructure-phases-or-named-workflow": (det_restructure, "turnover"),
    "project-specific-environment-commands": (det_project_cmds, "features"),
    "preserve-root-cause-first-while-compressing": (det_preserve_root_cause, "features"),
    "explicitly-declare-purposes-goals": (det_purpose_goals, "headings"),
}

# Mapping motif -> canonical synonyms used in aggregation (kept in sync with
# aggregate.py for the supporting-group sets).
from aggregate import CANONICAL  # noqa: E402


def main() -> None:
    rows = json.loads((OUT / "group_records_annotated.json").read_text(encoding="utf-8"))
    # rebuild rep rows for feature access using the cached pool
    import sys

    sys.path.insert(0, str(OUT.parent.parent / "src"))
    from pathlib import Path as _P
    from skillvariants.cli import _build_variant_pool  # noqa: E402

    pool_data = _build_variant_pool(
        "https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md",
        cache_dir=_P(OUT.parent.parent / ".cache" / "skillvariants"),
        max_pages=3,
    )
    pool = pool_data["pool"]
    support: dict[str, set[int]] = defaultdict(set)
    for r in rows:
        for canon, syns in CANONICAL.items():
            if r["motif_1"] in syns or r["motif_2"] in syns or r["motif_3"] in syns:
                support[canon].add(r["group_id"])

    result = {}
    for canon in sorted(CANONICAL):
        coverage, note = FEATURE_COVERAGE.get(canon, ("NO", "n/a"))
        det, basis = DETECTORS.get(canon, (None, None))
        members = set()
        records = {r["group_id"]: r for r in rows}
        # map records to pool rows
        by_repo_path = {(r.repo, r.path): r for r in pool}
        # annotate: find matching pool row via repository+path
        matched = {}
        for rid, rec in records.items():
            key = (rec["repository"], rec["path"])
            if key in by_repo_path:
                matched[rid] = by_repo_path[key]
        if det is not None:
            tp = sp = 0
            for rid, rec in records.items():
                rep = matched.get(rid)
                if rep is None:
                    continue
                body = rep.doc.body
                headings = rep.feats.headings
                args = {
                    "body": (body,),
                    "body+headers": (body, headings),
                    "headings": (headings,),
                    "features": (rep,),
                    "turnover": (headings, rep.mutation_features.heading_turnover),
                }[basis]
                hit = det(*args)
                is_support = rid in support[canon]
                if is_support:
                    sp += 1
                    if hit:
                        tp += 1
            precision = tp / sp if sp else None
            recall = None
        else:
            precision = recall = None
        result[canon] = {
            "coverage": coverage,
            "note": note,
            "support_groups": len(support[canon]),
            "detected_on_support": precision,
            "precision_approx": None,
        }

    print(f"{'motif':58s} coexist    note                                    sup  recall(sup)")
    for canon, v in sorted(result.items(), key=lambda kv: -kv[1]["support_groups"]):
        print(f"{canon:58s} {v['coverage']:8s} {v['note'][:36]:36s} {v['support_groups']:3d}  {v['detected_on_support']}")

    # worth_reviewing aggregation per qualifying motif
    worth_counts = {}
    for canon, gids in support.items():
        c = Counter(records[g]["worth_reviewing"] for g in gids)
        worth_counts[canon] = dict(c)
    print("\nworth_reviewing distribution per supporting group:")
    for canon, c in sorted(worth_counts.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"  {canon[:56]:56s} {c}")
    (OUT / "passb.txt").write_text(
        json.dumps({"coverage": result, "worth": worth_counts}, indent=1,
                   ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
