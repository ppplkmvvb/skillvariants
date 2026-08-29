"""Generic mutation-group review generator for cross-family falsification.

Usage: python run_family.py <frontend-design|brainstorming> <target-url>

Outputs per family into research/evidence-motifs/<family>/:
  <family>-group-worksheet.tsv   one row per mutation group (annotation columns)
  <family>-group-records.json    machine records
  <family>-review-bundle.txt     human-auditable evidence for coding
"""
from __future__ import annotations

import csv
import difflib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from skillvariants.cli import _build_variant_pool  # noqa: E402
from skillvariants.features import extract_features  # noqa: E402
from skillvariants.ranking import MIN_RELATEDNESS, group_variants  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
CACHE = ROOT / ".cache" / "skillvariants"
BASE = Path(__file__).resolve().parent

FAMILY_URLS = {
    "frontend-design": "https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md",
    "brainstorming": "https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md",
}


def default_branch(repo_slug: str, cache: dict) -> str:
    if repo_slug in cache:
        return cache[repo_slug]
    if repo_slug in ("obra/superpowers", "anthropics/skills"):
        branch = "main"
    else:
        branch = subprocess.run(
            ["gh", "api", f"repos/{repo_slug}", "--jq", ".default_branch"],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip() or ""
    cache[repo_slug] = branch
    return branch


def excerpt_lines(diff_lines: list[str], kind: str, limit: int = 3, width: int = 120) -> str:
    picked = [ln[1:] for ln in diff_lines if ln.startswith(kind)]
    picked = [ln.strip().replace("\t", " ")[:width] for ln in picked if ln.strip()]
    return " | ".join(picked[:limit])[:800]


def run(family: str) -> None:
    out = BASE / family
    out.mkdir(parents=True, exist_ok=True)
    url = FAMILY_URLS[family]
    pool_data = _build_variant_pool(url, cache_dir=CACHE, max_pages=3)
    pool = pool_data["pool"]
    target = pool_data["target_doc"]
    target_feats = extract_features(target)
    gated = [r for r in pool if r.relatedness >= MIN_RELATEDNESS]
    groups = group_variants(gated)

    branch_cache_path = out / "_branches.json"
    branch_cache = json.loads(branch_cache_path.read_text()) if branch_cache_path.exists() else {}

    rows = []
    bundle = []
    for gid, group in enumerate(groups, start=1):
        rep = group.representative
        mf = rep.mutation_features
        repo = rep.repo
        ref = rep.ref or default_branch(repo, branch_cache)
        url_link = f"https://github.com/{repo}/blob/{ref}/{rep.path}"
        diff = list(difflib.unified_diff(
            target.body.splitlines(), rep.doc.body.splitlines(), lineterm="", n=0))
        added = excerpt_lines(diff, "+")
        removed = excerpt_lines(diff, "-")
        rows.append({
            "family": family,
            "group_id": gid,
            "repository": repo,
            "path": rep.path,
            "ref": ref,
            "direct_skill_url": url_link,
            "archetype": group.dominant_type(),
            "relatedness_score": round(rep.relatedness, 3),
            "group_member_count": len(group.members),
            "occurrence_count": group.member_count,
            "length_delta": mf.length_delta_ratio,
            "added_headings": mf.headings_added_count,
            "removed_headings": mf.headings_removed_count,
            "added_commands": len(mf.command_set_added),
            "removed_commands": len(mf.command_set_removed),
            "added_cross_skill_refs": max(mf.cross_skill_ref_delta, 0),
            "removed_cross_skill_refs": max(-mf.cross_skill_ref_delta, 0),
            "routing_signals": "; ".join(rep.feats.routing_signals[:4]),
            "wrapper_signals": "; ".join(rep.feats.wrapper_signals[:4]),
            "workflow_structure_delta": round(mf.workflow_structure_delta, 3),
            "short_added_excerpt": added,
            "short_removed_excerpt": removed,
            "meaningful_behavior_change": "",
            "motif_1": "",
            "motif_2": "",
            "motif_3": "",
            "worth_reviewing": "",
            "notes": "",
        })
        bundle.append(f"### G{gid} {repo} | {rep.path} | [{group.dominant_type()}]")
        bundle.append(f"  rel={rep.relatedness:.2f} sim={rep.sim.token_set_ratio:.2f} "
                      f"members={len(group.members)} occ={group.member_count}")
        bundle.append(f"  len={mf.length_delta_ratio:+.2f} hdr(+{mf.headings_added_count}/"
                      f"-{mf.headings_removed_count}) cmds(+{len(mf.command_set_added)}/"
                      f"-{len(mf.command_set_removed)}) refs({mf.cross_skill_ref_delta:+d})")
        bundle.append(f"  headings={rep.feats.headings[:7]}")
        bundle.append(f"  routing={rep.feats.routing_signals[:3]} wrapper={rep.feats.wrapper_signals[:3]}")
        bundle.append(f"  ADD: {added[:260]}")
        bundle.append(f"  REM: {removed[:200]}")
        bundle.append(f"  body: {' '.join(rep.doc.body.split())[:220]}")
        bundle.append("")

    branch_cache_path.write_text(json.dumps(branch_cache))

    with (out / f"{family}-group-worksheet.tsv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    (out / f"{family}-group-records.json").write_text(
        json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / f"{family}-review-bundle.txt").write_text("\n".join(bundle), encoding="utf-8")

    from collections import Counter
    print(f"{family}: groups={len(rows)} archetypes={dict(Counter(r['archetype'] for r in rows))}")


if __name__ == "__main__":
    for fam in ("frontend-design", "brainstorming"):
        run(fam)
