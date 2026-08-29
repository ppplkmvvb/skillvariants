"""Shared helpers for CLI commands: evidence payload assembly."""
from __future__ import annotations

import difflib
from collections import Counter
from pathlib import Path

from .github import GitHubClient, GitHubError
from .parser import parse_github_url, parse_skill_md
from .ranking import MIN_RELATEDNESS, group_variants
from .similarity import normalize_for_hash, sha256

DEFAULT_MAX_PAGES = 3


def build_evidence_payload(
    url: str, cache_dir: Path | None = None, max_pages: int = DEFAULT_MAX_PAGES,
    evidence_builder=None, fetch_errors_out: list | None = None,
) -> dict:
    """Deterministic evidence payload (schema_version 1).

    Used by the `evidence` command and by the study runtime. When
    `evidence_builder` is provided (tests), it replaces live collection.
    """
    if evidence_builder is not None:
        return evidence_builder(url)
    if cache_dir is None:
        cache_dir = Path(".cache/skillvariants")
    client = GitHubClient(cache_dir=Path(cache_dir))
    target_ref = parse_github_url(url)
    doc = parse_skill_md(client.fetch_text(target_ref), source=target_ref)
    from .features import extract_features
    from .ranking import build_variant_row
    from .classify import classify_pair

    target = doc
    target_feats = extract_features(doc)
    name = target.name
    if not name:
        raise ValueError("target has no frontmatter name; cannot search")
    query = f'"name: {name}" filename:SKILL.md'
    hits = client.code_search(query, max_pages=max_pages)

    seen = set()
    candidates = []
    for hit in hits:
        key = (hit.repo, hit.path)
        if key in seen or hit.repo == "":
            continue
        seen.add(key)
        if hit.repo == target_ref.repo_slug and hit.path == target_ref.path:
            continue
        candidates.append(hit)

    target_hash = sha256(normalize_for_hash(target.raw))
    fetch_errors: list[str] = []
    exact_copies = 0
    by_hash: dict = {}
    for hit in candidates:
        try:
            text = client.fetch_text(hit.to_ref())
        except GitHubError as exc:
            fetch_errors.append(f"{hit.repo}/{hit.path}: {exc}")
            continue
        cdoc = parse_skill_md(text, source=hit.to_ref())
        full_hash = sha256(normalize_for_hash(cdoc.raw))
        if full_hash == target_hash:
            exact_copies += 1
        if full_hash in by_hash:
            by_hash[full_hash]["_copies"] += 1
            continue
        feats = extract_features(cdoc)
        sim = score_similarity(target, target_feats, cdoc, feats)
        classification = classify_pair(target, target_feats, cdoc, feats, sim)
        by_hash[full_hash] = {"doc": cdoc, "feats": feats, "sim": sim,
                              "classification": classification, "_copies": 1,
                              "hit": hit}
    from .ranking import build_variant_row as _bvr
    pool = []
    for full_hash, item in by_hash.items():
        row = _bvr(
            repo=item["hit"].repo, path=item["hit"].path, ref=item["hit"].default_branch,
            doc=item["doc"], feats=item["feats"], sim=item["sim"],
            classification=item["classification"], copy_count=item["_copies"],
            sha256_full=full_hash, target_doc=target, target_feats=target_feats,
            target_name=name,
        )
        pool.append(row)
    pool.sort(key=lambda r: r.sim.score, reverse=True)

    gated = [r for r in pool if r.relatedness >= MIN_RELATEDNESS]
    groups = group_variants(gated)
    archetype_counts = Counter(g.dominant_type() for g in groups)

    group_rows = []
    for gid, group in enumerate(groups, start=1):
        rep = group.representative
        mf = rep.mutation_features
        ref = rep.ref
        diff = list(difflib.unified_diff(
            target.body.splitlines(), rep.doc.body.splitlines(), lineterm="", n=0))
        added = [ln[1:].strip()[:160] for ln in diff if ln.startswith("+") and ln[1:].strip()]
        removed = [ln[1:].strip()[:160] for ln in diff if ln.startswith("-") and ln[1:].strip()]
        group_rows.append({
            "group_id": gid,
            "repository": rep.repo,
            "path": rep.path,
            "ref": ref,
            "direct_skill_url": f"https://github.com/{rep.repo}/blob/{ref}/{rep.path}",
            "archetype": group.dominant_type(),
            "relatedness": round(rep.relatedness, 3),
            "member_count": len(group.members),
            "occurrence_count": group.member_count,
            "structural_signals": {
                "length_delta": round(mf.length_delta_ratio, 3),
                "headings_added": mf.headings_added_count,
                "headings_removed": mf.headings_removed_count,
                "commands_added": mf.command_set_added,
                "commands_removed": mf.command_set_removed,
                "cross_skill_ref_delta": mf.cross_skill_ref_delta,
                "routing_signals": rep.feats.routing_signals[:6],
                "wrapper_signals": rep.feats.wrapper_signals[:6],
                "workflow_structure_delta": round(mf.workflow_structure_delta, 3),
                "placeholder_signal": round(rep.feats.placeholder_signal, 3),
            },
            "added_excerpt": " | ".join(added[:3])[:900],
            "removed_excerpt": " | ".join(removed[:3])[:900],
        })

    # resolve empty refs via gh api (memoized on disk)
    from .cli import _resolve_group_refs, _CACHE_DIR_STATE  # circular-safe import
    old_state = _CACHE_DIR_STATE
    try:
        import skillvariants.cli as cli_mod
        cli_mod._CACHE_DIR_STATE = Path(cache_dir)
        _resolve_group_refs(group_rows)
    finally:
        cli_mod._CACHE_DIR_STATE = old_state
    for row in group_rows:
        row["direct_skill_url"] = (
            f"https://github.com/{row['repository']}/blob/{row['ref']}/{row['path']}")

    if fetch_errors_out is not None:
        fetch_errors_out.extend(fetch_errors)

    return {
        "schema_version": "1",
        "target": {
            "repository": target_ref.repo_slug,
            "path": target_ref.path,
            "ref": target_ref.ref,
            "direct_skill_url": f"https://github.com/{target_ref.repo_slug}/blob/{target_ref.ref}/{target_ref.path}",
            "name": name,
            "normalized_hash": target_hash,
        },
        "summary": {
            "candidate_count": len(candidates),
            "related_variant_count": len(pool),
            "exact_copy_count": exact_copies,
            "mutation_group_count": len(groups),
            "broad_archetype_counts": dict(archetype_counts),
        },
        "groups": group_rows,
    }


from .similarity import score_similarity  # noqa: E402
