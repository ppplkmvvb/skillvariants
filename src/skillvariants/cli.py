"""skillvariants CLI: inspect / related / compare (archetype-first mutation explorer).

`related` exposes two ranking modes:
  --mode mutations  (default) archetype map of notable adaptation patterns
  --mode closest    pure similarity DESC after exact-copy collapse
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from .classify import classify_pair
from .features import SkillFeatures, extract_features
from .github import GitHubClient, GitHubError
from .parser import GitHubRef, parse_github_url, parse_skill_md
from .ranking import (
    MIN_RELATEDNESS,
    ARCHETYPE_HUMAN_LABELS,
    ArchetypeBucket,
    build_archetype_map,
    build_variant_row,
    group_variants,
    representative_score,
    _archetype_signals,
)
from .render import SimilarityRow, render_compare, render_inspect, render_mutations, render_related
from .similarity import normalize_for_hash, score_similarity, sha256

app = typer.Typer(
    help="SkillVariants: find copies and variants of Agent Skills across GitHub.",
    no_args_is_help=True,
)
console = Console()

DEFAULT_CACHE_DIR = ".cache/skillvariants"
DEFAULT_MAX_PAGES = 3


def _representative_view(group, archetype: str) -> tuple[float, list[str]]:
    """Score + signals for a group's representative under one archetype."""
    return (
        representative_score(group.representative, archetype),
        _archetype_signals(group.representative, archetype),
    )


def emit_json(data: dict | list) -> None:
    """All JSON output goes through here: never through Rich markup."""
    sys.stdout.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _load_doc(
    client: Any, url: str
) -> tuple[GitHubRef, Any, SkillFeatures]:
    ref = parse_github_url(url)
    doc = parse_skill_md(client.fetch_text(ref), source=ref)
    return ref, doc, extract_features(doc)


def _exit_usage(exc: Exception) -> None:
    if isinstance(exc, ValueError):
        raise typer.BadParameter(str(exc))
    raise typer.Exit(str(exc), code=1)


@app.command()
def inspect(
    url: str = typer.Argument(..., help="GitHub SKILL.md URL"),
    cache_dir: Path = typer.Option(DEFAULT_CACHE_DIR, "--cache-dir"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON"),
) -> None:
    """Show frontmatter, body stats, and signals for one Skill."""
    try:
        client = GitHubClient(cache_dir=cache_dir)
        ref, doc, feats = _load_doc(client, url)
    except (ValueError, GitHubError) as exc:
        _exit_usage(exc)
    if json_output:
        emit_json(
            {
                "ref": {
                    "owner": ref.owner,
                    "repo": ref.repo,
                    "ref": ref.ref,
                    "path": ref.path,
                },
                "name": doc.name,
                "frontmatter": doc.frontmatter,
                "body": {
                    "lines": feats.n_lines,
                    "characters": feats.n_chars,
                    "headings": feats.headings,
                    "code_blocks": feats.n_code_blocks,
                    "tables": feats.n_tables,
                    "bullets": feats.n_bullets,
                },
                "signals": {
                    "commands": feats.commands,
                    "urls": feats.urls,
                    "cross_skill_refs": feats.cross_skill_refs,
                    "routing_signals": feats.routing_signals,
                    "wrapper_signals": feats.wrapper_signals,
                    "canonical_ref": feats.canonical_ref,
                    "is_wrapper": feats.is_wrapper,
                },
            }
        )
    else:
        render_inspect(ref, doc, feats, console)


def _build_variant_pool(
    target_url: str,
    cache_dir: Path,
    max_pages: int,
    client: Any | None = None,
) -> dict:
    """Shared retrieval stage: fetch candidates, collapse exact copies,
    score every unique variant against the target."""
    if client is None:
        client = GitHubClient(cache_dir=cache_dir)
    target_ref, target, target_feats = _load_doc(client, target_url)
    name = target.name
    if not name:
        raise ValueError(
            "The target Skill has no `name` in its frontmatter; cannot search "
            "by name. Rerun with a different SKILL.md URL."
        )
    query = f'"name: {name}" filename:SKILL.md'
    hits = client.code_search(query, max_pages=max_pages)

    seen: set[tuple[str, str]] = set()
    candidates = []
    for hit in hits:
        key = (hit.repo, hit.path)
        # NOTE: an empty default_branch is legitimate -- the contents API
        # treats a blank ?ref= as the repository default branch (cached
        # first-spike searches rely on this).
        if key in seen or hit.repo == "":
            continue
        seen.add(key)
        if hit.repo == target_ref.repo_slug and hit.path == target_ref.path:
            continue  # the target itself
        candidates.append(hit)

    target_hash = sha256(normalize_for_hash(target.raw))
    fetch_errors: list[str] = []
    exact_copies_of_target = 0
    by_hash: dict[str, VariantRow] = {}
    fetched_count = 0

    for hit in candidates:
        try:
            text = client.fetch_text(hit.to_ref())
        except GitHubError as exc:
            fetch_errors.append(f"{hit.repo}/{hit.path}: {exc}")
            continue
        except FileNotFoundError as exc:  # only reachable via test fakes
            fetch_errors.append(f"{hit.repo}/{hit.path}: missing fixture {exc}")
            continue
        fetched_count += 1
        doc = parse_skill_md(text, source=hit.to_ref())
        full_hash = sha256(normalize_for_hash(doc.raw))
        if full_hash == target_hash:
            exact_copies_of_target += 1
        if full_hash in by_hash:
            by_hash[full_hash].copy_count += 1
            continue
        feats = extract_features(doc)
        sim = score_similarity(target, target_feats, doc, feats)
        classification = classify_pair(target, target_feats, doc, feats, sim)
        row = build_variant_row(
            repo=hit.repo,
            path=hit.path,
            ref=hit.default_branch,
            doc=doc,
            feats=feats,
            sim=sim,
            classification=classification,
            copy_count=1,
            sha256_full=full_hash,
            target_doc=target,
            target_feats=target_feats,
            target_name=name,
        )
        by_hash[full_hash] = row

    pool = sorted(by_hash.values(), key=lambda r: r.sim.score, reverse=True)
    return {
        "target": {"repo": target_ref.repo_slug, "path": target_ref.path, "name": name},
        "query": query,
        "counts": {
            "candidates_fetched": fetched_count,
            "candidates_total": len(candidates),
            "exact_copies_of_target": exact_copies_of_target,
            "unique_variants": len(pool),
        },
        "fetch_errors": fetch_errors,
        "pool": pool,
        "target_doc": target,
    }


def _payload_common(pool_data: dict, mode: str) -> dict:
    return {
        "target": pool_data["target"],
        "query": pool_data["query"],
        "mode": mode,
        "counts": pool_data["counts"],
        "fetch_errors": pool_data["fetch_errors"],
    }


def _print_fetch_errors(pool_data: dict) -> None:
    if pool_data["fetch_errors"]:
        for error in pool_data["fetch_errors"][:5]:
            console.print(f"[yellow]SKIPPED[/yellow] {error}")


_CACHE_DIR_STATE = Path(DEFAULT_CACHE_DIR)


def _default_branch(repo_slug: str, cache: dict) -> str:
    import subprocess

    if repo_slug in cache:
        return cache[repo_slug]
    result = subprocess.run(
        ["gh", "api", f"repos/{repo_slug}", "--jq", ".default_branch"],
        capture_output=True, text=True, timeout=30,
    )
    branch = result.stdout.strip() or "main"
    cache[repo_slug] = branch
    return branch


def _resolve_group_refs(group_rows: list[dict]) -> None:
    """Resolve empty refs (older search caches) to each repo's default branch.

    Memoized in-memory and persisted under the cache dir so reruns stay fast.
    """
    cache_path = _CACHE_DIR_STATE / "branches.json"
    cache: dict = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            cache = {}
    changed = False
    for row in group_rows:
        if row["ref"]:
            continue
        repo = row["repository"]
        try:
            row["ref"] = _default_branch(repo, cache)
            changed = True
        except Exception as exc:  # keep evidence flowing; surface on the group
            row["ref"] = "main"
            row["ref_resolution_note"] = str(exc)[:200]
    if changed:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(cache), encoding="utf-8")
        except OSError:
            pass


@app.command()
def evidence(
    url: str = typer.Argument(..., help="GitHub SKILL.md URL"),
    max_pages: int = typer.Option(DEFAULT_MAX_PAGES, "--max-pages", min=1, max=10),
    cache_dir: Path = typer.Option(DEFAULT_CACHE_DIR, "--cache-dir"),
) -> None:
    """Stable agent-facing evidence JSON (schema_version=1).

    stdout carries only JSON; progress/warnings go to stderr. Every group
    includes a direct SKILL.md URL so an agent can trace
    group -> representative file -> exact GitHub source.
    """
    global _CACHE_DIR_STATE
    _CACHE_DIR_STATE = cache_dir
    import difflib

    err_console = Console(file=sys.stderr)

    try:
        pool_data = _build_variant_pool(url, cache_dir, max_pages)
    except (ValueError, GitHubError) as exc:
        _exit_usage(exc)

    pool = pool_data["pool"]
    target_ref = parse_github_url(url)
    from .features import extract_features
    from .similarity import normalize_for_hash, sha256

    target_doc = pool_data["target_doc"]
    target_hash = sha256(normalize_for_hash(target_doc.raw))

    gated = [row for row in pool if row.relatedness >= MIN_RELATEDNESS]
    groups = group_variants(gated)

    from collections import Counter

    archetype_counts = Counter(g.dominant_type() for g in groups)

    group_rows = []
    for gid, group in enumerate(groups, start=1):
        rep = group.representative
        mf = rep.mutation_features
        row = {
            "group_id": gid,
            "repository": rep.repo,
            "path": rep.path,
            "ref": rep.ref,
            "direct_skill_url": "",
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
            "added_excerpt": "",
            "removed_excerpt": "",
        }
        diff = list(difflib.unified_diff(
            target_doc.body.splitlines(), rep.doc.body.splitlines(),
            lineterm="", n=0))
        added = [line[1:].strip()[:160] for line in diff
                 if line.startswith("+") and line[1:].strip()]
        removed = [line[1:].strip()[:160] for line in diff
                   if line.startswith("-") and line[1:].strip()]
        row["added_excerpt"] = " | ".join(added[:3])[:900]
        row["removed_excerpt"] = " | ".join(removed[:3])[:900]
        group_rows.append(row)

    _resolve_group_refs(group_rows)
    for row in group_rows:
        row["direct_skill_url"] = (
            f"https://github.com/{row['repository']}/blob/"
            f"{row['ref']}/{row['path']}"
        )

    payload = {
        "schema_version": "1",
        "target": {
            "repository": target_ref.repo_slug,
            "path": target_ref.path,
            "ref": target_ref.ref,
            "direct_skill_url": (
                f"https://github.com/{target_ref.repo_slug}/blob/"
                f"{target_ref.ref}/{target_ref.path}"
            ),
            "name": pool_data["target"]["name"],
            "normalized_hash": target_hash,
        },
        "summary": {
            "candidate_count": pool_data["counts"]["candidates_total"],
            "related_variant_count": pool_data["counts"]["unique_variants"],
            "exact_copy_count": pool_data["counts"]["exact_copies_of_target"],
            "mutation_group_count": len(groups),
            "broad_archetype_counts": dict(archetype_counts),
        },
        "groups": group_rows,
    }
    emit_json(payload)
    if pool_data["fetch_errors"]:
        for error in pool_data["fetch_errors"][:5]:
            err_console.print(f"[yellow]SKIPPED[/yellow] {error}")


def _build_mutations_payload(pool_data: dict, limit: int) -> dict:
    """Assemble the archetype-first mutations view (JSON schema, section 16)."""
    counts = pool_data["counts"]
    pool = pool_data["pool"]
    buckets, summary_counts = build_archetype_map(
        pool, representatives_per_archetype=limit
    )

    def archetype_payload(bucket: ArchetypeBucket) -> dict:
        representatives = []
        for group in bucket.ranked_groups[:limit]:
            rep = group.representative
            score, signals = _representative_view(group, bucket.archetype)
            representatives.append(
                {
                    "repository": rep.repo,
                    "path": rep.path,
                    "ref": rep.ref,
                    "sha256_full": rep.sha256_full,
                    "relatedness_score": round(rep.relatedness, 4),
                    "representative_score": round(score, 4),
                    "group_member_count": len(group.members),
                    "group_occurrence_count": group.member_count,
                    "similarity_percent": round(rep.sim.score * 100),
                    "primary_mutation_type": rep.classification.primary,
                    "labels": rep.classification.labels,
                    "signals": signals,
                    "description": rep.doc.description,
                    "body_excerpt": " ".join(rep.doc.body.split())[:400],
                }
            )
        return {
            "type": bucket.archetype,
            "label": ARCHETYPE_HUMAN_LABELS.get(bucket.archetype, bucket.archetype),
            "group_count": len(bucket.ranked_groups),
            "unique_variant_count": bucket.unique_variant_count,
            "occurrence_count": bucket.occurrence_count,
            "representatives": representatives,
        }

    return {
        "skill": {
            "name": pool_data["target"]["name"],
            "repository": pool_data["target"]["repo"],
            "path": pool_data["target"]["path"],
        },
        "query": pool_data["query"],
        "mode": "mutations",
        "exact_copy_count": counts["exact_copies_of_target"],
        "unique_related_variants": counts["unique_variants"],
        "counts": {**counts, **summary_counts},
        "min_relatedness": MIN_RELATEDNESS,
        "fetch_errors": pool_data["fetch_errors"],
        "archetypes": [archetype_payload(b) for b in buckets],
    }


@app.command()
def related(
    url: str = typer.Argument(..., help="GitHub SKILL.md URL"),
    mode: str = typer.Option(
        "mutations",
        "--mode",
        help="Ranking view: 'mutations' (archetype map, default) or 'closest'.",
    ),
    limit: int = typer.Option(10, "--limit", min=1, max=50),
    max_pages: int = typer.Option(DEFAULT_MAX_PAGES, "--max-pages", min=1, max=10),
    cache_dir: Path = typer.Option(DEFAULT_CACHE_DIR, "--cache-dir"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON"),
) -> None:
    """Find same-name variants: notable mutations (default) or closest copies."""
    if mode not in ("mutations", "closest"):
        raise typer.BadParameter("--mode must be 'mutations' or 'closest'")
    try:
        pool_data = _build_variant_pool(url, cache_dir, max_pages)
    except (ValueError, GitHubError) as exc:
        _exit_usage(exc)

    counts = pool_data["counts"]
    if mode == "closest":
        payload = _payload_common(pool_data, "closest")
        payload["rows"] = [row.summary() for row in pool_data["pool"][:limit]]
        if json_output:
            emit_json(payload)
            return
        rows = [
            SimilarityRow(
                rank=index,
                repo=row["repo"],
                path=row["path"],
                score=row["similarity_score"],
                label=row["label"]
                + (f" (x{row['copy_count']})" if row["copy_count"] > 1 else ""),
                description=row["description"] or "",
                copy_count=row["copy_count"],
            )
            for index, row in enumerate(payload["rows"], start=1)
        ]
        render_related(
            family_name=pool_data["target"]["name"] or "Unknown",
            total_candidates=counts["candidates_total"],
            rows=rows,
            exact_copies=counts["exact_copies_of_target"],
            unique_variants=min(limit, counts["unique_variants"]),
            console=console,
        )
        _print_fetch_errors(pool_data)
        return

    # ---- mutations mode (default): archetype-first view ------------------
    payload = _build_mutations_payload(pool_data, limit)
    if json_output:
        emit_json(payload)
        return
    render_mutations(
        skill_name=pool_data["target"]["name"] or "Unknown",
        total_candidates=counts["candidates_total"],
        payload=payload,
        console=console,
    )
    _print_fetch_errors(pool_data)


@app.command()
def compare(
    url_a: str = typer.Argument(..., help="First GitHub SKILL.md URL"),
    url_b: str = typer.Argument(..., help="Second GitHub SKILL.md URL"),
    cache_dir: Path = typer.Option(DEFAULT_CACHE_DIR, "--cache-dir"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON"),
) -> None:
    """Compare two Skills and classify the mutation between them."""
    try:
        client = GitHubClient(cache_dir=cache_dir)
        ref_a, doc_a, feats_a = _load_doc(client, url_a)
        ref_b, doc_b, feats_b = _load_doc(client, url_b)
        sim = score_similarity(doc_a, feats_a, doc_b, feats_b)
        classification = classify_pair(doc_a, feats_a, doc_b, feats_b, sim)
    except (ValueError, GitHubError) as exc:
        _exit_usage(exc)
    if json_output:
        emit_json(
            {
                "a": ref_a.slug,
                "b": ref_b.slug,
                "similarity": sim.as_dict(),
                "classification": classification.as_dict(),
            }
        )
    else:
        render_compare(
            ref_a, doc_a, feats_a, ref_b, doc_b, feats_b, sim, classification, console
        )


if __name__ == "__main__":
    app()
