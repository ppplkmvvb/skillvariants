"""skillvariants CLI: inspect / related / compare (archetype-first mutation explorer).

`related` exposes two ranking modes:
  --mode mutations  (default) archetype map of notable adaptation patterns
  --mode closest    pure similarity DESC after exact-copy collapse
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from typing import Any, NoReturn

import typer
from rich.console import Console

from .classify import classify_pair
from .features import SkillFeatures, extract_features
from .github import CACHE_MAX_AGE_SECONDS, GitHubClient, GitHubError
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
from .study import tasks as T
from .render import SimilarityRow, render_compare, render_inspect, render_mutations, render_related
from .similarity import normalize_for_hash, score_similarity, sha256

app = typer.Typer(
    help="SkillVariants: find copies and variants of Agent Skills across GitHub.",
    no_args_is_help=True,
)
console = Console()

DEFAULT_CACHE_DIR = ".cache/skillvariants"
DEFAULT_MAX_PAGES = 3


@dataclass(frozen=True)
class SourceOptions:
    refresh: bool = False
    offline: bool = False
    max_age_seconds: int = CACHE_MAX_AGE_SECONDS

    def client_kwargs(self) -> dict:
        # Keep default construction compatible with lightweight injected clients.
        return {key: value for key, value, default in (
            ('refresh', self.refresh, False), ('offline', self.offline, False),
            ('max_age_seconds', self.max_age_seconds, CACHE_MAX_AGE_SECONDS),
        ) if value != default}


@app.callback()
def main(
    ctx: typer.Context,
    refresh: bool = typer.Option(False, '--refresh', help='Refresh GitHub file and search caches.'),
    offline: bool = typer.Option(False, '--offline', help='Use cached GitHub sources only; no authentication or network.'),
    cache_max_age: int = typer.Option(CACHE_MAX_AGE_SECONDS, '--cache-max-age', min=0,
                                      help='Maximum mutable cache age in seconds; 0 always refreshes online.'),
) -> None:
    """Global source options go before the command name."""
    if refresh and offline:
        raise typer.BadParameter('--refresh and --offline cannot be used together.')
    ctx.obj = SourceOptions(refresh=refresh, offline=offline, max_age_seconds=cache_max_age)


def _source_options(ctx: typer.Context) -> dict:
    options = ctx.find_object(SourceOptions)
    return options.client_kwargs() if options else {}


def _representative_view(group, archetype: str) -> tuple[float, list[str]]:
    """Score + signals for a group's representative under one archetype."""
    return (
        representative_score(group.representative, archetype),
        _archetype_signals(group.representative, archetype),
    )


def emit_json(data: dict | list) -> None:
    """ASCII-safe JSON preserves Unicode even on legacy Windows streams."""
    def encode(value: Any) -> str:
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        raise TypeError(f"Cannot serialize {type(value).__name__} as JSON")
    sys.stdout.write(json.dumps(data, indent=2, ensure_ascii=True, default=encode) + "\n")


def _load_doc(
    client: Any, url: str
) -> tuple[GitHubRef, Any, SkillFeatures]:
    ref = parse_github_url(url)
    doc = (client.fetch_document(ref) if hasattr(client, "fetch_document")
           else parse_skill_md(client.fetch_text(ref), source=ref))
    ref = doc.source or ref
    return ref, doc, extract_features(doc)


def _exit_usage(exc: Exception) -> NoReturn:
    message = f"Error: {exc}"
    encoding = getattr(sys.stderr, "encoding", None) or "utf-8"
    message = message.encode(encoding, errors="backslashreplace").decode(encoding)
    typer.echo(message, err=True)
    raise typer.Exit(code=2 if isinstance(exc, ValueError) else 1)


EXPECTED_ERRORS = (ValueError, GitHubError, OSError, UnicodeError, T.SubmissionError)


def _load_input(value: str, cache_dir: Path, client: Any = None, *, github_options: dict | None = None):
    """Inspect/compare local UTF-8 files without creating a network client."""
    if "://" in value:
        parse_github_url(value)  # validate before credential lookup
        return _load_doc(client or GitHubClient(cache_dir=cache_dir, **(github_options or {})), value)
    path = Path(value).expanduser().resolve()
    doc = parse_skill_md(path.read_bytes().decode("utf-8"))
    doc.source_metadata = {"kind": "local", "path": str(path),
                           "raw_sha256": sha256(doc.raw)}
    ref = SimpleNamespace(slug=str(path), path=str(path), repo_slug="local file", ref="local")
    return ref, doc, extract_features(doc)


@app.command()
def inspect(
    ctx: typer.Context,
    url: str = typer.Argument(..., help="GitHub SKILL.md URL or local UTF-8 file"),
    cache_dir: Path = typer.Option(DEFAULT_CACHE_DIR, "--cache-dir"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON"),
) -> None:
    """Show frontmatter, body stats, and signals for one Skill."""
    try:
        ref, doc, feats = _load_input(url, cache_dir, github_options=_source_options(ctx))
    except EXPECTED_ERRORS as exc:
        _exit_usage(exc)
    if json_output:
        emit_json(
            {
                "ref": ({
                    "owner": ref.owner,
                    "repo": ref.repo,
                    "ref": ref.ref,
                    "path": ref.path,
                } if isinstance(ref, GitHubRef) else {"kind": "local", "path": ref.path}),
                "source": doc.source_metadata if hasattr(doc, "source_metadata") else {},
                "parse_errors": doc.parse_errors,
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
    *, github_options: dict | None = None,
) -> dict:
    """Shared retrieval stage: fetch candidates, collapse exact copies,
    score every unique variant against the target."""
    if client is None:
        client = GitHubClient(cache_dir=cache_dir, **(github_options or {}))
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
        # Search hits may omit a branch; the client resolves it before fetching.
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
            doc = (client.fetch_document(hit.to_ref()) if hasattr(client, "fetch_document")
                   else parse_skill_md(client.fetch_text(hit.to_ref()), source=hit.to_ref()))
        except GitHubError as exc:
            fetch_errors.append(f"{hit.repo}/{hit.path}: {exc}")
            continue
        except FileNotFoundError as exc:  # only reachable via test fakes
            fetch_errors.append(f"{hit.repo}/{hit.path}: missing fixture {exc}")
            continue
        fetched_count += 1
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
            ref=doc.source.ref if doc.source else hit.default_branch,
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
    related_count = sum(row.relatedness >= MIN_RELATEDNESS for row in pool)
    return {
        "target": {"repo": target_ref.repo_slug, "path": target_ref.path, "name": name},
        "query": query,
        "counts": {
            "candidates_fetched": fetched_count,
            "candidates_total": len(candidates),
            "candidates_failed": len(fetch_errors),
            "exact_copies_of_target": exact_copies_of_target,
            "unique_variants": len(pool),
            "related_unique_variants": related_count,
            "unrelated_unique_variants": len(pool) - related_count,
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


@app.command()
def evidence(
    ctx: typer.Context,
    url: str = typer.Argument(..., help="GitHub SKILL.md URL"),
    max_pages: int = typer.Option(DEFAULT_MAX_PAGES, "--max-pages", min=1, max=10),
    cache_dir: Path = typer.Option(DEFAULT_CACHE_DIR, "--cache-dir"),
    json_output: bool = typer.Option(True, "--json", help="Emit JSON (the default)"),
) -> None:
    """Paired source evidence JSON (schema_version=2).

    stdout carries only JSON; progress/warnings go to stderr. Every group
    includes a direct SKILL.md URL so an agent can trace
    group -> representative file -> exact GitHub source.
    """
    from .cli_helpers import build_evidence_payload
    err_console = Console(file=sys.stderr)
    fetch_errors: list[str] = []
    try:
        payload = build_evidence_payload(url, cache_dir, max_pages,
                                         fetch_errors_out=fetch_errors,
                                         github_options=_source_options(ctx))
    except EXPECTED_ERRORS as exc:
        _exit_usage(exc)
    emit_json(payload)
    for error in fetch_errors[:5]:
        err_console.print(f"[yellow]SKIPPED[/yellow] {error}")


# ---- study runtime commands (v0.2) ---------------------------------------------

def _runtime(base_dir: Path | None = None, batch_size: int = 8,
             *, github_options: dict | None = None, cache_dir: Path | None = None) -> "StudyRuntime":
    from .study.runtime import StudyRuntime
    from .cli_helpers import build_evidence_payload
    builder = (partial(build_evidence_payload, cache_dir=cache_dir, github_options=github_options)
               if github_options else None)
    return StudyRuntime(base_dir=base_dir, batch_size=batch_size, evidence_builder=builder)


def _study_emit(payload: dict) -> None:
    emit_json(payload)


@app.command()
def study_start(
    ctx: typer.Context,
    url: str = typer.Argument(..., help="GitHub SKILL.md URL"),
    cache_dir: Path = typer.Option(DEFAULT_CACHE_DIR, "--cache-dir"),
    base_dir: Path = typer.Option(Path("."), "--base-dir", help="Workspace root"),
    json_output: bool = typer.Option(True, "--json"),
) -> None:
    """Start (or resume) a persistent study session for a Skill."""
    try:
        options = _source_options(ctx)
        runtime = (_runtime(base_dir=base_dir, github_options=options, cache_dir=cache_dir)
                   if options else _runtime(base_dir=base_dir))
        result = runtime.start(url, cache_dir=cache_dir)
    except EXPECTED_ERRORS as exc:
        _exit_usage(exc)
    _study_emit(result)


@app.command()
def study_status(
    study_id: str = typer.Argument(...),
    base_dir: Path = typer.Option(Path("."), "--base-dir", help="Workspace root"),
    json_output: bool = typer.Option(True, "--json", help="Emit JSON (the default)"),
) -> None:
    """Show study manifest status and counts."""
    try:
        result = _runtime(base_dir=base_dir).status(study_id)
    except EXPECTED_ERRORS as exc:
        _exit_usage(exc)
    _study_emit(result)


@app.command()
def study_next(
    study_id: str = typer.Argument(...),
    base_dir: Path = typer.Option(Path("."), "--base-dir", help="Workspace root"),
    batch_size: int = typer.Option(8, "--batch-size", min=4, max=12),
    json_output: bool = typer.Option(True, "--json", help="Emit JSON (the default)"),
) -> None:
    """Return the next semantic task for the agent (or COMPLETE)."""
    try:
        result = _runtime(base_dir=base_dir, batch_size=batch_size).next_task(study_id)
    except EXPECTED_ERRORS as exc:
        _exit_usage(exc)
    _study_emit(result)


@app.command()
def study_submit(
    study_id: str = typer.Argument(...),
    task_result: Path = typer.Argument(..., help="Path to task-result JSON"),
    force: bool = typer.Option(False, "--force", help="Override conflicting resubmission"),
    base_dir: Path = typer.Option(Path("."), "--base-dir", help="Workspace root"),
    json_output: bool = typer.Option(True, "--json", help="Emit JSON (the default)"),
) -> None:
    """Submit a validated semantic task result."""
    try:
        response = json.loads(task_result.read_text(encoding="utf-8"))
        if not isinstance(response, dict):
            raise ValueError("Task result must be a JSON object")
        result = _runtime(base_dir=base_dir).submit(
            study_id, response.get("task_id", ""), response, force=force)
    except EXPECTED_ERRORS as exc:
        _exit_usage(exc)
    _study_emit(result)


@app.command()
def study_report(
    study_id: str = typer.Argument(...),
    base_dir: Path = typer.Option(Path("."), "--base-dir", help="Workspace root"),
    json_output: bool = typer.Option(True, "--json", help="Emit JSON (the default)"),
) -> None:
    """Emit the deterministic report.json for a completed study."""
    from .study.models import read_json
    from .study.storage import StudyStore
    try:
        store = StudyStore(base_dir)
        with store.locked(study_id):
            state = store.load(study_id)
            if state.manifest.get("status") != "COMPLETE":
                raise ValueError(f"Study {study_id} is not complete; run study-next {study_id}")
            root = store.study_path(study_id)
            if not all((root / name).is_file() for name in ("report.json", "report.md", "motifs.json")):
                raise ValueError("Completed study has missing report artifacts; restore a backup or regenerate the study")
            report = read_json(root / "report.json")
    except EXPECTED_ERRORS as exc:
        _exit_usage(exc)
    _study_emit(report)


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
        "unique_related_variants": counts["related_unique_variants"],
        "counts": {**counts, **summary_counts},
        "min_relatedness": MIN_RELATEDNESS,
        "fetch_errors": pool_data["fetch_errors"],
        "archetypes": [archetype_payload(b) for b in buckets],
    }


@app.command()
def related(
    ctx: typer.Context,
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
        pool_data = _build_variant_pool(url, cache_dir, max_pages, github_options=_source_options(ctx))
    except EXPECTED_ERRORS as exc:
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
    ctx: typer.Context,
    url_a: str = typer.Argument(..., help="First GitHub URL or local UTF-8 file"),
    url_b: str = typer.Argument(..., help="Second GitHub URL or local UTF-8 file"),
    cache_dir: Path = typer.Option(DEFAULT_CACHE_DIR, "--cache-dir"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON"),
) -> None:
    """Compare two Skills and classify the mutation between them."""
    try:
        ref_a, doc_a, feats_a = _load_input(url_a, cache_dir, github_options=_source_options(ctx))
        ref_b, doc_b, feats_b = _load_input(url_b, cache_dir, github_options=_source_options(ctx))
        sim = score_similarity(doc_a, feats_a, doc_b, feats_b)
        classification = classify_pair(doc_a, feats_a, doc_b, feats_b, sim)
    except EXPECTED_ERRORS as exc:
        _exit_usage(exc)
    if json_output:
        from .comparison import compare_documents
        emit_json(
            {
                "a": ref_a.slug,
                "b": ref_b.slug,
                "similarity": sim.as_dict(),
                "classification": classification.as_dict(),
                "comparison": compare_documents(doc_a, doc_b),
            }
        )
    else:
        render_compare(
            ref_a, doc_a, feats_a, ref_b, doc_b, feats_b, sim, classification, console
        )


if __name__ == "__main__":
    app()
