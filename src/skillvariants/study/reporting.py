"""Final report artifacts: deterministic report.json + report.md validation."""
from __future__ import annotations

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
        "schema_version": "1",
        "study_id": study_id,
        "target": target,
        "summary": {**counts, "sampling_applied": sampling_applied},
        "accepted_motifs": motifs["accepted"],
        "suppressed_motifs": motifs["suppressed"],
    }
