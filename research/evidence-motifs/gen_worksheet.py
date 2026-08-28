"""Depth validation helper: one review record per mutation group for
systematic-debugging (spec sections 5-6). Writes TSV worksheet with empty
annotation columns; evidence JSON kept alongside for the reviewer."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from skillvariants.cli import _build_variant_pool  # noqa: E402
from skillvariants.ranking import (  # noqa: E402
    MIN_RELATEDNESS,
    group_variants,
)

ROOT = Path(__file__).resolve().parent.parent.parent
CACHE = ROOT / ".cache" / "skillvariants"
OUT = ROOT / "research" / "evidence-motifs"
TARGET = "https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md"


def default_branch(repo_slug: str) -> str:
    cache = OUT / "_default_branches.json"
    data = json.loads(cache.read_text()) if cache.exists() else {}
    if repo_slug in data:
        return data[repo_slug]
    if repo_slug in ("obra/superpowers",):
        branch = "main"
    else:
        branch = subprocess.run(
            ["gh", "api", f"repos/{repo_slug}", "--jq", ".default_branch"],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip() or ""
    data[repo_slug] = branch
    cache.write_text(json.dumps(data))
    return branch


def excerpt_lines(diff_lines: list[str], kind: str, limit: int = 3, width: int = 140) -> str:
    picked = [ln[1:] for ln in diff_lines if ln.startswith(kind)]
    picked = [ln.strip().replace("\t", " ")[:width] for ln in picked if ln.strip()]
    return " | ".join(picked[:limit])[:900]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pool_data = _build_variant_pool(TARGET, cache_dir=CACHE, max_pages=3)
    pool = pool_data["pool"]
    target = pool_data["target_doc"]
    from skillvariants.features import extract_features

    target_feats = extract_features(target)
    gated = [r for r in pool if r.relatedness >= MIN_RELATEDNESS]
    groups = group_variants(gated)

    rows = []
    for gid, group in enumerate(groups, start=1):
        rep = group.representative
        mf = rep.mutation_features
        repo = rep.repo
        ref = rep.ref or default_branch(repo)
        url = f"https://github.com/{repo}/blob/{ref}/{rep.path}"
        # diff-based added/removed lines
        import difflib
        diff = list(difflib.unified_diff(
            target.body.splitlines(), rep.doc.body.splitlines(), lineterm="", n=0))
        added = excerpt_lines(diff, "+")
        removed = excerpt_lines(diff, "-")
        rows.append({
            "group_id": gid,
            "repository": repo,
            "path": rep.path,
            "ref": ref,
            "direct_skill_url": url,
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
            "placeholder_signal": round(rep.feats.placeholder_signal, 3),
            "short_added_excerpt": added,
            "short_removed_excerpt": removed,
            "meaningful_behavior_change": "",
            "motif_1": "",
            "motif_2": "",
            "motif_3": "",
            "worth_reviewing": "",
            "notes": "",
        })

    with open(OUT / "systematic-debugging-group-worksheet.tsv", "w", encoding="utf-8",
              newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    with open(OUT / "group_records.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)

    from collections import Counter
    types = Counter(r["archetype"] for r in rows)
    print(f"groups={len(rows)} archetypes={dict(types)}")


if __name__ == "__main__":
    main()
