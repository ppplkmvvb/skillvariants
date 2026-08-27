"""Rich-based terminal rendering for inspect / related / compare.

Rendering is strictly separated from logic; the same data is also
available via --json for evaluation.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .classify import Classification, mutation_summary
from .features import SkillFeatures
from .parser import GitHubRef, SkillDoc
from .similarity import ScoreBreakdown

MAX_DIFF_LINES = 60


@dataclass
class SimilarityRow:
    rank: int
    repo: str
    path: str
    score: float
    label: str
    description: str
    copy_count: int


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def render_inspect(
    ref: GitHubRef,
    doc: SkillDoc,
    feats: SkillFeatures,
    console: Console | None = None,
) -> None:
    console = console or Console()
    console.print(
        Panel(
            Text()
            .append(f"Skill: {doc.name or '(no name)'}\n")
            .append(f"Repository: {ref.repo_slug}\n")
            .append(f"Path: {ref.path}\n")
            .append(f"Ref: {ref.ref}"),
            title="Skill",
        )
    )
    if doc.parse_errors:
        console.print(
            Panel("\n".join(doc.parse_errors), title="Parse warnings", style="yellow")
        )
    fm_lines = [f"{key}: {value}" for key, value in doc.frontmatter.items()]
    console.print(Panel("\n".join(fm_lines) if fm_lines else "(empty frontmatter)", title="Frontmatter"))
    console.print(
        Panel(
            "\n".join(
                [
                    f"lines: {feats.n_lines}",
                    f"characters: {feats.n_chars}",
                    f"headings: {len(feats.headings)}",
                    f"code blocks: {feats.n_code_blocks}",
                    f"tables: {feats.n_tables}",
                    f"bullets: {feats.n_bullets}",
                ]
            ),
            title="Body",
        )
    )
    signals = [
        f"shell commands: {', '.join(feats.commands) if feats.commands else 'none'}",
        f"external URLs: {len(feats.urls)}",
        f"cross-skill references: {', '.join(feats.cross_skill_refs) if feats.cross_skill_refs else 'none'}",
        f"canonical wrapper: {str(bool(feats.is_wrapper)).lower()}",
        f"routing signals: {', '.join(feats.routing_signals) or 'none'}",
        f"wrapper signals: {', '.join(feats.wrapper_signals) or 'none'}",
    ]
    console.print(Panel("\n".join(signals), title="Signals"))


def render_related(
    family_name: str,
    total_candidates: int,
    rows: list[SimilarityRow],
    exact_copies: int,
    unique_variants: int,
    clone_band_count: int = 0,
    console: Console | None = None,
) -> None:
    console = console or Console()
    console.print(Text(f"\n{family_name.upper()}", style="bold"))
    console.print(f"Candidate matches found: {total_candidates:,}\n")
    table = Table(show_header=True, header_style="bold")
    table.add_column("#", justify="right")
    table.add_column("Similarity", justify="right")
    table.add_column("Repository")
    table.add_column("Path")
    table.add_column("Type")
    for row in rows:
        table.add_row(
            str(row.rank),
            _fmt_pct(row.score),
            row.repo,
            row.path,
            row.label,
        )
    console.print(table)
    summary = [f"{exact_copies:,} exact copies collapsed"]
    if clone_band_count:
        summary.append(f"{clone_band_count:,} near-identical clones aggregated")
    summary.append(f"{unique_variants:,} unique variants shown")
    console.print(f"\n{', '.join(summary)}")


def render_mutations(
    skill_name: str,
    total_candidates: int,
    payload: dict,
    console: Console | None = None,
    representatives_per_section: int = 3,
) -> None:
    """Archetype-first view (spike 3): one section per detected mutation
    archetype, in the stable product order, no cross-archetype ranking."""
    console = console or Console()
    console.print(Text(f"\n{skill_name.upper()}", style="bold"))
    console.print(f"Candidate matches found: {total_candidates:,}\n")

    counts = payload["counts"]
    lines = [
        f"Exact copies              {payload['exact_copy_count']:,}",
        f"Unique related variants   {payload['unique_related_variants']:,}",
        f"Detected mutation archetypes {len(payload['archetypes'])}",
        f"Mutation groups           {counts.get('mutation_groups_total', 0):,}",
    ]
    if counts.get("unclassified_occurrences"):
        lines.append(
            f"Unclassified variants     "
            f"{counts.get('unclassified_unique_variants', 0):,} files / "
            f"{counts.get('unclassified_occurrences', 0):,} occurrences"
        )
    for line in lines:
        console.print(f"  {line}")
    console.print()

    shown_any = False
    for archetype in payload["archetypes"]:
        shown_any = True
        console.print(Text(archetype["label"].upper(), style="bold"))
        console.print(
            f"{archetype['group_count']} groups · "
            f"{archetype['unique_variant_count']} unique variants · "
            f"{archetype['occurrence_count']} occurrences"
        )
        console.print("─" * 45)
        for rep in archetype["representatives"][:representatives_per_section]:
            console.print(Text(rep["repository"], style="cyan bold"))
            console.print(f"  relatedness: {rep['relatedness_score']:.2f}")
            console.print(
                f"  {rep['group_member_count']} variant file(s) in group"
                + (f", {rep['group_occurrence_count']} occurrences" if rep["group_occurrence_count"] != rep["group_member_count"] else "")
            )
            for signal in rep["signals"][1:]:  # skip 'classified as' line here
                console.print(f"  {signal}")
            console.print()
    if not shown_any:
        console.print("  (no related variants passed the relatedness gate)")


def render_compare(
    target_ref: GitHubRef | None,
    target: SkillDoc,
    target_feats: SkillFeatures,
    candidate_ref: GitHubRef | None,
    candidate: SkillDoc,
    candidate_feats: SkillFeatures,
    sim: ScoreBreakdown,
    classification: Classification,
    console: Console | None = None,
    max_diff_lines: int = MAX_DIFF_LINES,
) -> None:
    console = console or Console()
    summary = mutation_summary(target, target_feats, candidate, candidate_feats, sim, classification)

    header = (
        f"A: {target_ref.slug if target_ref else '(fixture)'}\n"
        f"B: {candidate_ref.slug if candidate_ref else '(fixture)'}"
    )
    console.print(Panel(header, title="Compare"))

    lines = [
        f"Similarity          {_fmt_pct(sim.score)}  (name match: {sim.name_match})",
        f"Token similarity    {_fmt_pct(sim.token_set_ratio)}",
        f"Length              {summary['length_change']}",
        f"Headings            {summary['workflow_headings']}",
        f"Code blocks         {summary['code_blocks'][0]} -> {summary['code_blocks'][1]}",
        f"Cross-skill refs    {summary['cross_skill_refs'][0]} -> {summary['cross_skill_refs'][1]}",
        f"Shell commands      {summary['commands'][0]} -> {summary['commands'][1]}",
        "",
        "Detected mutation:",
        f"  {classification.primary}",
    ]
    if len(classification.labels) > 1:
        lines[0] = lines[0]
        lines.append(f"  all labels: {', '.join(classification.labels)}")
    console.print(Panel("\n".join(lines), title="Summary"))

    structural = ["Added headings", "Removed / compressed"]
    added = summary["added_headings"]
    removed = summary["removed_headings"]
    added_rules = summary["added_rules"]
    removed_rules = summary["removed_rules"]
    preserved_rules = summary["preserved_rules"]

    section_lines: list[str] = []
    section_lines.append("Added concepts")
    for word in added[:10]:
        section_lines.append(f"+ {word}")
    for rule in added_rules[:6]:
        section_lines.append(f"+ rule: {rule}")
    section_lines.append("Removed / compressed")
    for word in removed[:10]:
        section_lines.append(f"- {word}")
    for rule in removed_rules[:6]:
        section_lines.append(f"- rule: {rule}")
    if preserved_rules:
        section_lines.append("Preserved")
        for rule in preserved_rules[:6]:
            section_lines.append(f"= {rule}")
    if not added and not removed and not added_rules and not removed_rules:
        section_lines.append("(no heading-level or ALL-CAPS rule changes)")
    console.print(Panel("\n".join(section_lines), title="Structural changes"))

    target_lines = target.body.splitlines()
    candidate_lines = candidate.body.splitlines()
    diff = list(
        difflib.unified_diff(
            target_lines,
            candidate_lines,
            fromfile=(target_ref.slug if target_ref else "A"),
            tofile=(candidate_ref.slug if candidate_ref else "B"),
            lineterm="",
            n=1,
        )
    )
    shown = diff[:max_diff_lines]
    if len(diff) > max_diff_lines:
        shown = shown + [f"... ({len(diff) - max_diff_lines} more diff lines)"]
    console.print(Panel("\n".join(shown), title="Text diff"))
