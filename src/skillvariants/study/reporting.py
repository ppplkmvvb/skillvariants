"""Final report artifacts: deterministic report.json + report.md validation."""
from __future__ import annotations

import html
import re
from urllib.parse import urlparse

from .models import SCHEMA_VERSION

REQUIRED_SECTIONS = (
    "Target Skill", "Corpus summary", "Recurring adaptations",
    "Notable one-offs", "Caveats",
)

FORBIDDEN_PHRASES = (
    "best practice", "best variant", "widely adopted",
    "independently invented", "recommendation score",
)


def missing_sections(report_md: str) -> list[str]:
    lowered = (report_md or "").lower()
    return [s for s in REQUIRED_SECTIONS if s.lower() not in lowered]


def forbidden_phrases_present(report_md: str) -> list[str]:
    lowered = (report_md or "").lower()
    return [p for p in FORBIDDEN_PHRASES if p in lowered]


def build_report_json(study_id: str, target: dict, counts: dict,
                      motifs: dict, sampling_applied: bool) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "study_id": study_id,
        "target": target,
        "summary": {**counts, "sampling_applied": sampling_applied},
        "accepted_motifs": motifs["accepted"],
        "suppressed_motifs": motifs["suppressed"],
    }


def empty_report_md(target: dict, counts: dict, motifs: dict) -> str:
    suppressions = "\n".join(
        f"- {m['label']}: {m['status']}. {'; '.join(m.get('reasons', []))}"
        for m in motifs["suppressed"]) or "No motifs were proposed."
    return (
        f"# Experimental Skill study\n\n## Target Skill\n\n{target['direct_skill_url']}\n\n"
        f"## Corpus summary\n\nAnalyzed {counts['groups_analyzed']} of "
        f"{counts['groups_total']} selected groups. "
        f"Unresolved source evidence: {counts.get('groups_unresolved', 0)} groups.\n\n"
        "## Recurring adaptations\n\nNo recurring motif passed verification and guardrails.\n\n"
        f"## Notable one-offs\n\nProposal dispositions (not verified claims):\n\n{suppressions}\n\n"
        "## Caveats\n\nThis is an experimental interpretation of a bounded corpus. "
        "Suppressed or unverified proposals are not evidence of recurring behavior. "
        "Repetition does not establish quality or independent adoption.\n"
    )


def _inline(value) -> str:
    """Keep source and analyst strings from creating document structure."""
    text = html.escape(" ".join(str(value).split()), quote=False)
    return re.sub(r"([\\`*_{}\[\]<>#+|])", r"\\\1", text)


def _link(label: str, url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "github.com":
        return _inline(label)
    return f"[{_inline(label)}](<{url.replace('>', '%3E').replace('<', '%3C')}>)"


def _citation_lines(evidence: dict, target: dict, variant: dict) -> list[str]:
    result = []
    for side, source in (("a", target), ("b", variant)):
        citation = evidence.get(side)
        if not citation:
            continue
        start, end = citation["start_line"], citation["end_line"]
        url = source.get("direct_skill_url", "").split("#", 1)[0]
        label = f"{side.upper()} · lines {start}–{end}"
        result.extend([f"{_link(label, url + f'#L{start}-L{end}')} · SHA-256 `{citation['raw_sha256']}`", ""])
        fence = "`" * max(3, 1 + max((len(s) for s in re.findall(r"`+", citation["quote"])), default=0))
        result.extend([fence + "text", citation["quote"], fence, ""])
    return result


def render_report_md(report: dict) -> str:
    """Render authoritative structure/counts from validated JSON, not agent prose.

    Invariants and directions remain agent interpretations even after separate
    verification; exact quotation checks cannot prove semantic entailment.
    """
    target, counts = report["target"], report["summary"]
    lines = ["# Experimental Skill study", "", "## Target Skill", "",
             _link(target.get("direct_skill_url", "Target"), target.get("direct_skill_url", "")), "",
             "## Corpus summary", "",
             f"Analyzed {counts['groups_analyzed']} of {counts['groups_total']} selected groups. "
             f"Unresolved source evidence: {counts.get('groups_unresolved', 0)} groups. "
             f"Pending groups: {counts.get('groups_pending', 0)}.", "",
             f"Sampling applied: {str(counts.get('sampling_applied', False)).lower()}. "
             f"Available groups before selection: {counts.get('total_groups_available', counts['groups_total'])}.", "",
             "## Recurring adaptations", "",
             "Directions and invariants below are agent interpretations reviewed against paired source evidence. "
             "Counts are computed by the engine; quotation checks establish source integrity, not meaning.", ""]
    for motif in report["accepted_motifs"]:
        lines.extend([f"### {_inline(motif.get('display_name', motif['label']))}", "",
                      f"Direction: **{_inline(motif['change_type'])}**. "
                      f"Observed in {motif['group_count']} groups across {motif['repository_count']} repositories.", "",
                      "Agent interpretation: " + _inline(motif["invariant"]), ""])
        for group in motif["supporting_groups"]:
            lines.extend([f"Group {group['group_id']} · " + _link(group.get("repository", "Source"), group.get("direct_skill_url", "")), ""])
            lines.extend(_citation_lines(group.get("evidence", {}), target, group))
    if not report["accepted_motifs"]:
        lines.extend(["No recurring motif passed verification and guardrails.", ""])
    lines.extend(["## Notable one-offs", "",
                  "Initial paired observations below have not been separately verified as recurring adaptations.", ""])
    for group in report.get("individual_observations", []):
        lines.extend([f"### Group {group['group_id']}", ""])
        for motif in group["motifs"]:
            lines.extend([f"**{_inline(motif['change_type'])}** · {_inline(motif['action'])}", "",
                          "Initial interpretation: " + _inline(motif["invariant"]), ""])
            lines.extend(_citation_lines(motif["evidence"], target, group))
    if not report.get("individual_observations"):
        lines.extend(["No additional paired observations are listed.", ""])
    if report["suppressed_motifs"]:
        lines.extend(["Proposal dispositions:", ""])
        for motif in report["suppressed_motifs"]:
            lines.append(f"- {_inline(motif['label'])}: {_inline(motif['status'])}. "
                         + _inline("; ".join(motif.get("reasons", []))))
        lines.append("")
    lines.extend(["## Caveats", "",
                  "This is an experimental interpretation of a bounded corpus. Repetition does not establish "
                  "quality, ancestry, independent adoption, or observed agent behavior. Local snippets do not "
                  "prove global absence. A completed workflow can still contain unresolved source evidence.", "",
                  "Optional analyst notes, when submitted, are saved separately as analyst-notes.md and are not "
                  "part of this generated report.", ""])
    return "\n".join(lines)
