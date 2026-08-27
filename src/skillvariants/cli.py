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
