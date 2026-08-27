"""Deterministic mutation classification between a target skill and a candidate.

Every label comes with human-readable evidence so nothing is asserted without
a traceable reason (spec section 14, risk E).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .features import (
    PROJECT_PHRASES,
    SkillFeatures,
    uppercase_rules,
)
from .parser import SkillDoc
from .similarity import ScoreBreakdown, copy_labels

# Display/canonical priority when several labels apply.
LABEL_PRIORITY: tuple[str, ...] = (
    "exact-copy",
    "body-copy-with-metadata-change",
    "compatibility-wrapper",
    "routing-specialization",
    "compact-rewrite",
    "expanded-guidance",
    "workflow-specialization",
    "project-specialization",
)

PROJECT_PHRASE_RE = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in PROJECT_PHRASES) + r")\b",
    re.IGNORECASE,
)


@dataclass
class Classification:
    labels: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    @property
    def primary(self) -> str:
        return self.labels[0] if self.labels else "no-label"

    def as_dict(self) -> dict:
        return {"labels": self.labels, "primary": self.primary, "evidence": self.evidence}


def classify_pair(
    target: SkillDoc,
    target_feats: SkillFeatures,
    candidate: SkillDoc,
    candidate_feats: SkillFeatures,
    sim: ScoreBreakdown,
) -> Classification:
    labels: list[str] = []
    evidence: list[str] = []

    target_len = max(len(target.body), 1)
    ratio = len(candidate.body) / target_len

    copies = copy_labels(target, candidate)
    if copies:
        labels.extend(copies)
        if copies[0] == "exact-copy":
            evidence.append("normalized full-file SHA-256 hashes are equal")
        else:
            evidence.append("normalized body hashes equal; frontmatter differs")

    same_name = sim.name_match

    if candidate_feats.is_wrapper and same_name:
        labels.append("compatibility-wrapper")
        evidence.append(
            f"short body ({candidate_feats.n_lines} lines) with canonical reference"
            + (f" -> {candidate_feats.canonical_ref}" if candidate_feats.canonical_ref else "")
        )

    if same_name and not copies:
        if (
            0.0 < ratio <= 0.5
            and 0.30 <= sim.token_set_ratio < 0.60
            and not candidate_feats.is_wrapper
        ):
            labels.append("compact-rewrite")
            evidence.append(
                f"body length {ratio:.0%} of reference; token similarity "
                f"{sim.token_set_ratio:.0%}"
            )
        elif ratio >= 1.3 and sim.token_set_ratio >= 0.45:
            labels.append("expanded-guidance")
            evidence.append(
                f"body length {ratio:.0%} of reference; token similarity "
                f"{sim.token_set_ratio:.0%}"
            )

        new_routing = set(candidate_feats.routing_signals) - set(
            target_feats.routing_signals
        )
        new_refs = set(candidate_feats.cross_skill_refs) - set(
            target_feats.cross_skill_refs
        )
        if (
            new_routing
            and sim.token_set_ratio >= 0.30
            and (len(new_routing) >= 2 or len(new_refs) >= 1)
        ):
            labels.append("routing-specialization")
            evidence.append(
                f"new routing signals: {sorted(new_routing)[:4]}; "
                f"new skill references: {sorted(new_refs)[:4] or 'none'}"
            )

        # Tightened in spike 2 (spec section 13): workflow-specialization must
        # show real workflow-structure evidence -- a genuine turnover of named
        # sections -- instead of firing on generic textual drift.
        headings_removed_count = len(
            {h.lower() for h in target_feats.headings}
            - {h.lower() for h in candidate_feats.headings}
        )
        headings_added_count = len(
            {h.lower() for h in candidate_feats.headings}
            - {h.lower() for h in target_feats.headings}
        )
        if (
            sim.token_set_ratio >= 0.30
            and headings_removed_count + headings_added_count >= 3
            and sim.heading_jaccard < 0.70
            and not candidate_feats.is_wrapper
        ):
            labels.append("workflow-specialization")
            evidence.append(
                f"workflow structure reworked: "
                f"{headings_removed_count} headings removed, "
                f"{headings_added_count} added"
                f" ({len(target_feats.headings)} -> {len(candidate_feats.headings)})"
            )

        project_signals = PROJECT_PHRASE_RE.findall(candidate.body)
        if len(set(project_signals)) >= 2:
            labels.append("project-specialization")
            evidence.append(f"project-specific phrases: {sorted(set(project_signals))}")

    ordered = [label for label in LABEL_PRIORITY if label in labels]
    return Classification(labels=ordered, evidence=evidence)


def mutation_summary(
    target: SkillDoc,
    target_feats: SkillFeatures,
    candidate: SkillDoc,
    candidate_feats: SkillFeatures,
    sim: ScoreBreakdown,
    classification: Classification,
) -> dict:
    """Deterministic, human-readable mutation summary (spec section 15)."""
    target_len = max(len(target.body), 1)
    ratio = len(candidate.body) / target_len
    target_headings = {h.lower() for h in target_feats.headings}
    candidate_headings = {h.lower() for h in candidate_feats.headings}

    target_rules = set(uppercase_rules(target.body))
    candidate_rules = set(uppercase_rules(candidate.body))

    delta = (len(candidate.body) - len(target.body)) / target_len
    return {
        "type": classification.primary,
        "labels": classification.labels,
        "length_change": f"{delta:+.0%}",
        "workflow_headings": (
            f"{len(target_feats.headings)} -> {len(candidate_feats.headings)} headings"
        ),
        "preserved_rules": sorted(target_rules & candidate_rules),
        "added_rules": sorted(candidate_rules - target_rules),
        "removed_rules": sorted(target_rules - candidate_rules),
        "added_headings": sorted(candidate_headings - target_headings),
        "removed_headings": sorted(target_headings - candidate_headings),
        "code_blocks": (target_feats.n_code_blocks, candidate_feats.n_code_blocks),
        "cross_skill_refs": (
            len(target_feats.cross_skill_refs),
            len(candidate_feats.cross_skill_refs),
        ),
        "commands": (len(target_feats.commands), len(candidate_feats.commands)),
    }
