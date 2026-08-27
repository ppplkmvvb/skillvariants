"""Deterministic ranking redesign (second spike).

Pipeline (spec section 7):

    candidate retrieval -> exact-copy collapse -> relatedness gate
    -> mutation feature vector -> variant grouping -> representative
    selection -> diversity-aware mutation ranking

Every score is a plain function of inspectable features; no embeddings, no LLM.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from rapidfuzz import fuzz

from .classify import Classification
from .features import SkillFeatures
from .parser import SkillDoc
from .similarity import ScoreBreakdown

# Relatedness gate. Calibrated on the first-spike fixtures/evaluation data:
#   known variants carry real content evidence (PilotDeck body similarity
#   0.44, Loopkit 0.52, Vibe-Skills / SuperAntigravity > 0.83); different-name
#   negative controls scored <= 0.27 overall; same-name noise (a "sample"
#   document about an unrelated topic) reached 0.41 almost entirely from the
#   name-match bonus plus tiny set-inflation effects.
# Rule: a name match only counts when backed by at least one strong content
# signal -- body similarity >= NAME_MATCH_MIN_BODY (0.40), or heading
# Jaccard >= 0.35, or description similarity >= 0.55 -- unless the candidate's
# frontmatter carries a canonical reference pointing at the target skill
# (WRAPPER_FLOOR), which is direct evidence of relation even for tiny bodies.
MIN_RELATEDNESS = 0.33
NAME_MATCH_MIN_BODY = 0.40
WRAPPER_FLOOR = 0.45

# Near-clone grouping threshold (spec section 14): bodies this similar are one
# mutation neighborhood, not independent results.
GROUP_SIMILARITY_THRESHOLD = 0.90

# Rows whose computed mutation magnitude falls below this are treated as one
# near-copy neighborhood regardless of mutual drift: GitHub clone fields are
# star-shaped (each copy is ~95%+ similar to the reference, but copies drift
# apart from EACH OTHER), so pairwise-only union-find never merges them.
NEAR_COPY_MAGNITUDE = 0.15

# MMR body-overlap penalty is retired with the global leaderboard view.
# Archetype-first ordering replaces it (third spike).

# Symmetric log-ratio length normalization cap (spec section 10). Chosen
# generically BEFORE looking at evaluation data: +/-K x span maps onto [0,1],
# so x2 == /2, x4 == /4, and x10 > x2 by construction. K=4 covers the
# practical adaptation range without saturating early.
import math

LENGTH_LOG_CAP_K = 4.0

# Stable product order of archetype sections (spec section 14). Sections are
# never reordered by score.
ARCHETYPE_ORDER: tuple[str, ...] = (
    "compact-rewrite",
    "expanded-guidance",
    "routing-specialization",
    "workflow-specialization",
    "project-specialization",
    "compatibility-wrapper",
)


def normalized_length_change(target_len: int, candidate_len: int) -> float:
    """Symmetric log-ratio length change normalized to [0, 1].

    x2 expansion equals /2 compression; saturation only at K-fold either way.
    """
    if target_len <= 0 or candidate_len <= 0:
        return 1.0 if target_len != candidate_len else 0.0
    log_ratio = abs(math.log(candidate_len / target_len))
    return min(log_ratio / math.log(LENGTH_LOG_CAP_K), 1.0)

RELATEDNESS_WEIGHTS = {
    "token_set_ratio": 0.55,
    "heading_jaccard": 0.15,
    "description": 0.20,
    "name_match": 0.10,
}


@dataclass
class MutationFeatures:
    """Deterministic delta features between a target skill and a variant."""

    text_similarity: float = 0.0
    length_delta_ratio: float = 0.0          # signed raw ratio (display)
    symmetric_length_change: float = 0.0     # log-ratio, normalized [0,1]
    heading_count_delta: int = 0
    heading_set_distance: float = 0.0
    heading_turnover: int = 0                # added + removed heading names
    headings_added_count: int = 0
    headings_removed_count: int = 0
    code_block_delta: int = 0
    command_set_added: list[str] = field(default_factory=list)
    command_set_removed: list[str] = field(default_factory=list)
    cross_skill_ref_delta: int = 0
    url_delta: int = 0
    wrapper_state_change: bool = False
    routing_signal_added: bool = False
    workflow_structure_delta: float = 0.0
    frontmatter_key_delta: int = 0
    description_delta: float = 0.0
    full_text_coherence: float = 1.0         # fuzz.ratio; absorber detector

    def as_dict(self) -> dict:
        return {
            "text_similarity": round(self.text_similarity, 4),
            "length_delta_ratio": round(self.length_delta_ratio, 4),
            "symmetric_length_change": round(self.symmetric_length_change, 4),
            "heading_count_delta": self.heading_count_delta,
            "heading_set_distance": round(self.heading_set_distance, 4),
            "heading_turnover": self.heading_turnover,
            "headings_added_count": self.headings_added_count,
            "headings_removed_count": self.headings_removed_count,
            "code_block_delta": self.code_block_delta,
            "command_set_added": self.command_set_added,
            "command_set_removed": self.command_set_removed,
            "cross_skill_ref_delta": self.cross_skill_ref_delta,
            "url_delta": self.url_delta,
            "wrapper_state_change": self.wrapper_state_change,
            "routing_signal_added": self.routing_signal_added,
            "workflow_structure_delta": round(self.workflow_structure_delta, 4),
            "frontmatter_key_delta": self.frontmatter_key_delta,
            "description_delta": round(self.description_delta, 4),
            "full_text_coherence": round(self.full_text_coherence, 4),
        }


def build_mutation_features(
    target: SkillDoc,
    target_feats: SkillFeatures,
    candidate: SkillDoc,
    candidate_feats: SkillFeatures,
    sim: ScoreBreakdown,
) -> MutationFeatures:
    target_len = max(len(target.body), 1)
    length_delta = (len(candidate.body) - len(target.body)) / target_len
    target_headings = {h.lower() for h in target_feats.headings}
    cand_headings = {h.lower() for h in candidate_feats.headings}
    removed = target_headings - cand_headings
    added = cand_headings - target_headings
    max_headings = max(len(target_headings), len(cand_headings), 1)
    return MutationFeatures(
        text_similarity=sim.token_set_ratio,
        length_delta_ratio=length_delta,
        symmetric_length_change=normalized_length_change(
            len(target.body), len(candidate.body)
        ),
        heading_count_delta=len(cand_headings) - len(target_headings),
        heading_set_distance=1.0 - sim.heading_jaccard,
        heading_turnover=len(removed) + len(added),
        headings_added_count=len(added),
        headings_removed_count=len(removed),
        code_block_delta=candidate_feats.n_code_blocks - target_feats.n_code_blocks,
        command_set_added=sorted(set(candidate_feats.commands) - set(target_feats.commands)),
        command_set_removed=sorted(set(target_feats.commands) - set(candidate_feats.commands)),
        cross_skill_ref_delta=(
            len(candidate_feats.cross_skill_refs) - len(target_feats.cross_skill_refs)
        ),
        url_delta=len(candidate_feats.urls) - len(target_feats.urls),
        wrapper_state_change=bool(candidate_feats.is_wrapper),
        routing_signal_added=bool(
            set(candidate_feats.routing_signals) - set(target_feats.routing_signals)
        ),
        workflow_structure_delta=(len(removed) + len(added)) / max_headings,
        frontmatter_key_delta=len(set(candidate.frontmatter) ^ set(target.frontmatter)),
        description_delta=1.0 - sim.description_similarity,
        full_text_coherence=fuzz.ratio(target.body, candidate.body) / 100.0,
    )


def _canonical_ref_points_at_target(doc: SkillDoc, target_name: str | None) -> bool:
    """True when a canonical_skill-style pointer resolves to the target skill.

    On GitHub every SKILL.md file ends with `SKILL.md`; the skill identifier
    lives in the parent directory name (`skills/<name>/SKILL.md`). Match either
    the file stem or the last path component before the file.
    """
    if not doc.canonical_ref or not target_name:
        return False
    parts = [p for p in doc.canonical_ref.rstrip("/").split("/") if p]
    if not parts:
        return False
    file_stem = parts[-1].removesuffix(".md")
    parent_dir = parts[-2].removesuffix(".md") if len(parts) >= 2 else ""
    return target_name in {file_stem.lower(), parent_dir.lower()}


def relatedness_score(
    sim: ScoreBreakdown,
    candidate: SkillDoc,
    target_name: str | None,
) -> tuple[float, list[str]]:
    """Conservative gate score; returns (score, evidence)."""
    raw = (
        RELATEDNESS_WEIGHTS["token_set_ratio"] * sim.token_set_ratio
        + RELATEDNESS_WEIGHTS["heading_jaccard"] * sim.heading_jaccard
        + RELATEDNESS_WEIGHTS["description"] * sim.description_similarity
        + (RELATEDNESS_WEIGHTS["name_match"] if sim.name_match else 0.0)
    )
    evidence: list[str] = []
    if sim.name_match:
        evidence.append(f"exact skill name match ({target_name})")
    if sim.token_set_ratio >= 0.5:
        evidence.append(f"body token similarity {sim.token_set_ratio:.0%}")
    if sim.description_similarity >= 0.6:
        evidence.append(f"description similarity {sim.description_similarity:.0%}")

    content_evidence = (
        sim.token_set_ratio >= NAME_MATCH_MIN_BODY
        or sim.heading_jaccard >= 0.35
        or sim.description_similarity >= 0.55
    )
    has_canonical = _canonical_ref_points_at_target(candidate, target_name)
    if has_canonical and raw < WRAPPER_FLOOR:
        evidence.append(
            f"frontmatter canonical reference to '{target_name}' "
            f"({candidate.canonical_ref})"
        )
        raw = WRAPPER_FLOOR
    elif sim.name_match and not content_evidence and not has_canonical:
        # Name-only match: the name is shared but nothing in the content
        # corroborates relation. Cap below the gate so generic same-name
        # collisions cannot enter mutation ranking on their name alone.
        evidence.append("name-only match without content corroboration; capped")
        raw = min(raw, MIN_RELATEDNESS - 0.03)
    return min(raw, 1.0), evidence


def mutation_magnitude(mf: MutationFeatures) -> tuple[float, list[str]]:
    """How materially different is this related skill? Returns (score, signals).

    Length uses the symmetric log-ratio term (spec section 10): a x20 absorber
    earns the same as a x4 rewrite, never more.
    """
    signals: list[str] = []

    length_term = mf.symmetric_length_change * 0.25
    if abs(mf.length_delta_ratio) >= 0.25:
        direction = "decreased" if mf.length_delta_ratio < 0 else "increased"
        signals.append(f"length {direction} by {abs(mf.length_delta_ratio):.0%}")

    structure_term = (
        min(mf.heading_set_distance, 1.0) * 0.175
        + min(abs(mf.heading_count_delta) / 8.0, 1.0) * 0.075
    )
    if mf.heading_turnover >= 3:
        signals.append(f"{mf.heading_turnover} headings added/removed")

    commands_changed = len(mf.command_set_added) + len(mf.command_set_removed)
    command_term = min(commands_changed / 5.0, 1.0) * 0.10
    if commands_changed:
        signals.append(
            f"shell-command set changed (+{len(mf.command_set_added)}/"
            f"-{len(mf.command_set_removed)})"
        )

    ref_term = min(abs(mf.cross_skill_ref_delta) / 4.0, 1.0) * 0.10
    if abs(mf.cross_skill_ref_delta) >= 2:
        sign = "+" if mf.cross_skill_ref_delta > 0 else ""
        signals.append(f"cross-skill references {sign}{mf.cross_skill_ref_delta}")

    routing_term = 0.10 if mf.routing_signal_added else 0.0
    if mf.routing_signal_added:
        signals.append("new routing-boundary language")
    wrapper_term = 0.08 if mf.wrapper_state_change else 0.0

    url_term = min(abs(mf.url_delta) / 4.0, 1.0) * 0.05

    magnitude = (
        length_term
        + structure_term
        + command_term
        + ref_term
        + routing_term
        + wrapper_term
        + url_term
    )
    return min(magnitude, 1.0), signals


LABELED_TYPES = {
    "compact-rewrite",
    "expanded-guidance",
    "routing-specialization",
    "compatibility-wrapper",
    "workflow-specialization",
    "project-specialization",
}


def explainability(classification: Classification) -> float:
    return 1.0 if classification.primary in LABELED_TYPES else 0.6


@dataclass
class VariantRow:
    repo: str
    path: str
    ref: str
    sha256_full: str
    copy_count: int
    doc: SkillDoc
    feats: SkillFeatures
    sim: ScoreBreakdown
    classification: Classification
    mutation_features: MutationFeatures
    relatedness: float
    relatedness_evidence: list[str]
    magnitude: float
    magnitude_signals: list[str]
    interest: float
    interest_signals: list[str]

    def summary(self) -> dict:
        return {
            "repo": self.repo,
            "path": self.path,
            "ref": self.ref,
            "sha256_full": self.sha256_full,
            "copy_count": self.copy_count,
            "name_match": self.sim.name_match,
            "similarity_score": round(self.sim.score, 4),
            "token_similarity": round(self.sim.token_set_ratio, 4),
            "label": self.classification.primary,
            "labels": self.classification.labels,
            "relatedness_score": round(self.relatedness, 4),
            "mutation_magnitude": round(self.magnitude, 4),
            "mutation_interest_score": round(self.interest, 4),
            "signals": self.interest_signals[:6],
            "description": self.doc.description,
            "headings": self.feats.headings,
            "body_excerpt": " ".join(self.doc.body.split())[:600],
            "n_lines": self.feats.n_lines,
            "n_chars": self.feats.n_chars,
        }


@dataclass
class MutationGroup:
    group_id: int
    members: list[VariantRow]
    representative: VariantRow
    similarity_range: tuple[float, float]

    @property
    def member_count(self) -> int:
        return sum(member.copy_count for member in self.members)

    def dominant_type(self) -> str:
        counts: dict[str, int] = {}
        for member in self.members:
            primary = member.classification.primary
            if primary in LABELED_TYPES:
                counts[primary] = counts.get(primary, 0) + member.copy_count
        if not counts:
            # fall back to the representative's own label (may be no-label)
            return self.representative.classification.primary
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def similarity_span_text(self) -> str:
        low = int(round(min(self.similarity_range) * 100))
        high = int(round(max(self.similarity_range) * 100))
        if low == high:
            return f"{high}%"
        return f"{low}-{high}%"

    def as_dict(self) -> dict:
        rep = self.representative
        return {
            "group_id": self.group_id,
            "member_variants": len(self.members),
            "member_occurrences": self.member_count,
            "primary_mutation_type": self.dominant_type(),
            "representative_labels": rep.classification.labels,
            "similarity_range_percent": [
                round(min(self.similarity_range) * 100),
                round(max(self.similarity_range) * 100),
            ],
            "interest_rank_scores": {
                "relatedness_score": round(rep.relatedness, 4),
                "mutation_magnitude": round(rep.magnitude, 4),
                "mutation_interest_score": round(rep.interest, 4),
            },
            "signals": rep.interest_signals[:6],
            "repository": rep.repo,
            "path": rep.path,
            "all_repositories": sorted({m.repo for m in self.members}),
            "representative": rep.summary(),
        }


def build_variant_row(
    *,
    repo: str,
    path: str,
    ref: str,
    doc: SkillDoc,
    feats: SkillFeatures,
    sim: ScoreBreakdown,
    classification: Classification,
    copy_count: int = 1,
    sha256_full: str = "",
    target_doc: SkillDoc | None = None,
    target_feats: SkillFeatures | None = None,
    target_name: str | None = None,
) -> VariantRow:
    """Assemble one scored variant from its computed pieces."""
    if target_doc is None or target_feats is None:
        raise ValueError("target_doc and target_feats are required")
    mf = build_mutation_features(target_doc, target_feats, doc, feats, sim)
    relatedness, relatedness_evidence = relatedness_score(sim, doc, target_name)
    magnitude, magnitude_signals = mutation_magnitude(mf)
    expl = explainability(classification)
    interest = min(relatedness * magnitude * expl, 1.0)
    signals = list(relatedness_evidence[:2]) + list(magnitude_signals)
    labels = ", ".join(classification.labels) or "no structural label"
    signals.insert(
        0,
        f"classified as {labels}" + (" (multiple)" if len(classification.labels) > 1 else ""),
    )
    return VariantRow(
        repo=repo,
        path=path,
        ref=ref,
        sha256_full=sha256_full,
        copy_count=copy_count,
        doc=doc,
        feats=feats,
        sim=sim,
        classification=classification,
        mutation_features=mf,
        relatedness=relatedness,
        relatedness_evidence=relatedness_evidence,
        magnitude=magnitude,
        magnitude_signals=magnitude_signals,
        interest=interest,
        interest_signals=signals,
    )


def pairwise_body_similarity(left: VariantRow, right: VariantRow) -> float:
    """Full-text similarity used for grouping edges.

    Deliberately NOT token_set_ratio: set-based scores treat an absorber file
    (target embedded inside unrelated bulk) as a near-perfect match of its
    victim, which would merge them into one group. Raw sequence ratio keeps
    true reformatted clones at ~1.0 while exposing absorbers at ~0.05.
    """
    return fuzz.ratio(left.doc.body, right.doc.body) / 100.0


def group_variants(rows: list[VariantRow]) -> list[MutationGroup]:
    """Two-stage grouping (spec section 14).

    Stage 1 -- hub partition: rows whose mutation magnitude is below
    NEAR_COPY_MAGNITUDE are one near-copy neighborhood. They cluster around the
    reference, not around each other, so magnitude is the honest grouping key.

    Stage 2 -- union-find over pairwise body similarity >=
    GROUP_SIMILARITY_THRESHOLD within the materially-changed remainder.

    Representative = medoid-like member with the highest summed within-group
    body similarity; for the hub group it is the most-related member.
    """
    near_copies = [row for row in rows if row.magnitude < NEAR_COPY_MAGNITUDE]
    rest = [row for row in rows if row.magnitude >= NEAR_COPY_MAGNITUDE]

    n = len(rest)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    sims: dict[tuple[int, int], float] = {}
    for i in range(n):
        for j in range(i + 1, n):
            value = pairwise_body_similarity(rest[i], rest[j])
            sims[(i, j)] = value
            if value >= GROUP_SIMILARITY_THRESHOLD:
                union(i, j)

    clusters: dict[int, list[int]] = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(i)

    def build_group(indices: list[int], members: list[VariantRow]) -> MutationGroup:
        if len(members) == 1 or len(indices) == 1:
            rep = members[0]
        else:
            totals = {i: 0.0 for i in indices}
            for (a, b), value in sims.items():
                if a in totals and b in totals:
                    totals[a] += value
                    totals[b] += value
            rep_index = max(
                indices,
                key=lambda i: (
                    totals[i],
                    rest[i].relatedness,
                ),
            )
            rep = rest[rep_index]
        ranges = [m.sim.score for m in members]
        return MutationGroup(
            group_id=0,
            members=list(members),
            representative=rep,
            similarity_range=(min(ranges), max(ranges)),
        )

    groups: list[MutationGroup] = []
    if near_copies:
        rep = max(
            near_copies,
            key=lambda r: r.relatedness,
        )
        groups.append(
            MutationGroup(
                group_id=0,
                members=near_copies,
                representative=rep,
                similarity_range=(
                    min(m.sim.score for m in near_copies),
                    max(m.sim.score for m in near_copies),
                ),
            )
        )
    for indices in sorted(clusters.values(), key=lambda idxs: -len(idxs)):
        groups.append(build_group(indices, [rest[i] for i in indices]))

    for gid, group in enumerate(groups):
        group.group_id = gid
    return groups


def interest_score(row: VariantRow) -> float:
    magnitude, mag_signals = mutation_magnitude(row.mutation_features)
    row.magnitude = magnitude
    row.magnitude_signals = mag_signals
    expl = explainability(row.classification)
    interest = row.relatedness * magnitude * expl
    signals = list(row.relatedness_evidence[:2]) + mag_signals
    if row.classification.labels:
        labels = ", ".join(row.classification.labels)
        signals.insert(0, f"classified as {row.classification.primary} ({labels})" if len(
            row.classification.labels) > 1 else f"classified as {labels}")
    signals.append(f"explainability {expl:.0%}")
    row.interest = min(interest, 1.0)
    row.interest_signals = signals
    return row.interest


# ---------------------------------------------------------------------------
# Archetype-first product model (third spike): bucket groups by primary
# mutation type and rank representatives WITHIN each archetype only.
# ---------------------------------------------------------------------------

ARCHETYPE_HUMAN_LABELS = {
    "compact-rewrite": "Compact rewrites",
    "expanded-guidance": "Expanded guidance",
    "routing-specialization": "Routing specializations",
    "workflow-specialization": "Workflow specializations",
    "project-specialization": "Project specializations",
    "compatibility-wrapper": "Compatibility wrappers",
}

ABSORBER_COHERENCE_FLOOR = 0.30  # fuzz.ratio below this on a much-larger file


def _archetype_signals(row: VariantRow, archetype: str) -> list[str]:
    """Deterministic per-archetype evidence lines for a representative."""
    mf = row.mutation_features
    signals = [f"classified as {row.classification.primary}"]
    if archetype == "compact-rewrite":
        signals.append(f"length changed by {mf.length_delta_ratio:+.0%}")
        if mf.heading_turnover:
            signals.append(f"{mf.heading_turnover} headings added/removed")
        if mf.command_set_added or mf.command_set_removed:
            signals.append(
                f"shell commands +{len(mf.command_set_added)}/-{len(mf.command_set_removed)}"
            )
        if not (mf.headings_added_count or mf.command_set_added):
            signals.append("caution: deletion-only rewrite (nothing added)")
    elif archetype == "expanded-guidance":
        if abs(mf.length_delta_ratio) >= 2.0 and mf.full_text_coherence < ABSORBER_COHERENCE_FLOOR:
            signals.append(
                f"caution: giant file ({mf.length_delta_ratio:+.0%}) whose text is "
                f"only {mf.full_text_coherence:.0%} contiguous match to the reference"
            )
        signals.append(f"+{mf.headings_added_count} new sections")
        if mf.full_text_coherence < ABSORBER_COHERENCE_FLOOR:
            signals.append(f"text coherence {mf.full_text_coherence:.0%} of reference span")
    elif archetype == "routing-specialization":
        if mf.routing_signal_added:
            signals.append("new routing-boundary language")
        if mf.cross_skill_ref_delta > 0:
            signals.append(f"+{mf.cross_skill_ref_delta} cross-skill references")
        for line in row.feats.routing_signals[:3]:
            signals.append(f"routing evidence: {line}")
    elif archetype == "compatibility-wrapper":
        if row.doc.canonical_ref:
            signals.append(f"canonical pointer -> {row.doc.canonical_ref}")
        for phrase in row.feats.wrapper_signals[:3]:
            if phrase.startswith("frontmatter"):
                continue
            signals.append(f"wrapper language: {phrase}")
        signals.append(f"body size {row.feats.n_lines} lines")
    elif archetype == "workflow-specialization":
        signals.append(
            f"workflow structure reworked "
            f"(+{mf.headings_added_count}/-{mf.headings_removed_count} sections)"
        )
        if row.classification.primary == "workflow-specialization":
            pass
    elif archetype == "project-specialization":
        signals.append(f"+{mf.frontmatter_key_delta} frontmatter key changes")
    return signals[:6]


def _archetype_raw_score(row: VariantRow, archetype: str) -> float | None:
    """Archetype-specific quality formula (spec section 11 of the final spike).

    Returns None for unknown archetypes; the caller falls back to relatedness.
    """
    rel = row.relatedness
    mf = row.mutation_features

    if archetype == "compact-rewrite":
        score = (
            0.40 * rel
            + 0.25 * mf.symmetric_length_change
            + 0.20 * mf.text_similarity
        )
        if "workflow-specialization" in row.classification.labels:
            score += 0.10  # restructuring, not just deletion
        if not (mf.headings_added_count or mf.command_set_added):
            score -= 0.15  # deletion-only variants are weaker stories
        return min(max(score, 0.0), 1.0)

    if archetype == "expanded-guidance":
        score = (
            0.40 * rel
            + 0.20 * min(mf.symmetric_length_change, 1.0)
            + 0.20 * min(mf.headings_added_count / 6.0, 1.0)
            + 0.10 * min(len(mf.command_set_added) / 3.0, 1.0)
            + 0.10 * mf.full_text_coherence
        )
        # Absorber resistance: a file many times larger than the reference
        # whose contiguous text barely matches it is mostly unrelated content.
        if (
            mf.length_delta_ratio >= 2.0
            and mf.full_text_coherence < ABSORBER_COHERENCE_FLOOR
        ):
            score *= 0.4
            score -= 0.10
        return min(max(score, 0.0), 1.0)

    if archetype == "routing-specialization":
        routing_strength = min(len(row.feats.routing_signals) / 4.0, 1.0)
        ref_growth = min(max(mf.cross_skill_ref_delta, 0) / 4.0, 1.0)
        score = 0.45 * rel + 0.25 * routing_strength + 0.20 * ref_growth
        return min(max(score, 0.0), 1.0)

    if archetype == "compatibility-wrapper":
        canonical_confidence = 1.0 if row.doc.canonical_ref else 0.5
        language_strength = min(len(row.feats.wrapper_signals) / 3.0, 1.0)
        name_relation = 1.0 if row.sim.name_match else 0.5
        score = 0.35 * canonical_confidence + 0.35 * language_strength + 0.30 * name_relation
        return min(max(score, 0.0), 1.0)

    if archetype == "workflow-specialization":
        planning_evidence = min(mf.heading_turnover / 8.0, 1.0)
        env_process = (
            1.0
            if any("mode" in s.lower() or "process" in s.lower()
                   for s in row.feats.routing_signals + row.feats.headings)
            else 0.5
        )
        score = 0.40 * rel + 0.30 * mf.workflow_structure_delta + 0.15 * planning_evidence \
            + 0.15 * env_process
        return min(max(score, 0.0), 1.0)

    if archetype == "project-specialization":
        import re as _re

        project_terms = len(_re.findall(r"\b(this project|this repository|migration|legacy|planning mode)\b", row.doc.body, _re.IGNORECASE))
        score = (
            0.40 * rel
            + 0.30 * min(project_terms / 4.0, 1.0)
            + 0.15 * min(abs(mf.frontmatter_key_delta) / 3.0, 1.0)
            + 0.15 * mf.workflow_structure_delta
        )
        return min(max(score, 0.0), 1.0)

    return None


# Placeholder/template documents make weak representative stories even when
# their structural shape matches an archetype. Uniform multiplicative penalty
# applied on top of every archetype formula (production fix, spec section 7).
PLACEHOLDER_PENALTY = 0.60


def representative_score(row: VariantRow, archetype: str) -> float:
    """Intra-archetype representative quality in [0, 1].

    The archetype formula is penalized by the document's placeholder density,
    so fill-in-the-blank skeletons rank below genuine rewrites without being
    excluded from discovery.
    """
    raw = _archetype_raw_score(row, archetype)
    if raw is None:
        return row.relatedness
    penalized = raw * (1.0 - PLACEHOLDER_PENALTY * row.feats.placeholder_signal)
    return min(max(penalized, 0.0), 1.0)


@dataclass
class ArchetypeBucket:
    archetype: str
    ranked_groups: list[MutationGroup]  # ALL qualifying groups, best first

    @property
    def unique_variant_count(self) -> int:
        return sum(len(g.members) for g in self.ranked_groups)

    @property
    def occurrence_count(self) -> int:
        return sum(g.member_count for g in self.ranked_groups)


def build_archetype_map(
    pool: list[VariantRow],
    representatives_per_archetype: int = 3,
) -> tuple[list[ArchetypeBucket], dict]:
    """Gate, group, then bucket by dominant primary type.

    Returns (buckets in stable ARCHETYPE_ORDER order with up to
    `representatives_per_archetype` top-scored groups each, plus summary
    counts including unclassified/near-copy tallies).
    """
    gated = [row for row in pool if row.relatedness >= MIN_RELATEDNESS]
    groups = group_variants(gated)

    buckets_map: dict[str, list[MutationGroup]] = {}
    unclassified_groups = 0
    unclassified_files = 0
    unclassified_occurrences = 0
    hub_group_files = 0
    hub_group_occurrences = 0

    for group in groups:
        primary = group.dominant_type()
        is_hub = group.members and all(
            m.magnitude < NEAR_COPY_MAGNITUDE for m in group.members
        ) and len(group.members) > 1
        if primary == "no-label":
            unclassified_groups += 1
            unclassified_files += len(group.members)
            unclassified_occurrences += group.member_count
            if is_hub:
                hub_group_files += len(group.members)
                hub_group_occurrences += group.member_count
            continue
        buckets_map.setdefault(primary, []).append(group)

    buckets: list[ArchetypeBucket] = []
    for archetype in ARCHETYPE_ORDER:
        groups_in = buckets_map.get(archetype, [])
        if not groups_in:
            continue
        ranked = sorted(
            groups_in,
            key=lambda g: representative_score(g.representative, archetype),
            reverse=True,
        )
        buckets.append(ArchetypeBucket(archetype, ranked))

    summary_counts = {
        "gated_out_by_relatedness": len(pool) - len(gated),
        "mutation_groups_total": len(groups),
        "unclassified_groups": unclassified_groups,
        "unclassified_unique_variants": unclassified_files,
        "unclassified_occurrences": unclassified_occurrences,
        "near_copy_hub_variants": hub_group_files,
        "near_copy_hub_occurrences": hub_group_occurrences,
    }
    return buckets, summary_counts
