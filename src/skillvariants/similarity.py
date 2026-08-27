"""Normalization, similarity scoring, and exact-copy hashing.

The scoring is intentionally simple and explainable (spec section 11):
name match gets a bonus, body token similarity dominates, and structure
(headings) plus description similarity refine the rank.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from rapidfuzz import fuzz

from .features import SkillFeatures
from .parser import SkillDoc

NAME_MATCH_BONUS = 0.32
WEIGHTS = {
    "token_set_ratio": 0.50,
    "char_ratio": 0.20,
    "heading_jaccard": 0.15,
    "description": 0.15,
}


def normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalize_for_hash(text: str) -> str:
    """Line endings unified, trailing whitespace stripped, outer blanks removed."""
    lines = normalize_line_endings(text).split("\n")
    stripped = [line.rstrip() for line in lines]
    while stripped and stripped[0] == "":
        stripped.pop(0)
    while stripped and stripped[-1] == "":
        stripped.pop()
    return "\n".join(stripped)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class ScoreBreakdown:
    name_match: bool
    token_set_ratio: float  # 0..1
    char_ratio: float  # 0..1
    heading_jaccard: float  # 0..1
    description_similarity: float  # 0..1
    name_bonus: float  # 0..1
    score: float  # 0..1

    def as_dict(self) -> dict:
        return {
            "name_match": self.name_match,
            "token_set_ratio": round(self.token_set_ratio, 4),
            "char_ratio": round(self.char_ratio, 4),
            "heading_jaccard": round(self.heading_jaccard, 4),
            "description_similarity": round(self.description_similarity, 4),
            "name_bonus": self.name_bonus,
            "score": round(self.score, 4),
        }


def jaccard(left: set, right: set) -> float:
    if not left and not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def score_similarity(
    target: SkillDoc,
    target_feats: SkillFeatures,
    candidate: SkillDoc,
    candidate_feats: SkillFeatures,
) -> ScoreBreakdown:
    token_set_ratio = (
        fuzz.token_set_ratio(target.body, candidate.body) / 100.0
    )
    max_len = max(len(target.body), len(candidate.body))
    char_ratio = (
        min(len(target.body), len(candidate.body)) / max_len if max_len else 1.0
    )
    heading_jaccard = jaccard(
        {h.lower() for h in target_feats.headings},
        {h.lower() for h in candidate_feats.headings},
    )
    desc_sim = fuzz.token_set_ratio(
        target.description or "", candidate.description or ""
    ) / 100.0

    name_match = (
        target.name is not None and target.name == candidate.name
    )
    name_bonus = NAME_MATCH_BONUS if name_match else 0.0

    raw = (
        WEIGHTS["token_set_ratio"] * token_set_ratio
        + WEIGHTS["char_ratio"] * char_ratio
        + WEIGHTS["heading_jaccard"] * heading_jaccard
        + WEIGHTS["description"] * desc_sim
    )
    score = min(1.0, raw + name_bonus)
    return ScoreBreakdown(
        name_match=name_match,
        token_set_ratio=token_set_ratio,
        char_ratio=char_ratio,
        heading_jaccard=heading_jaccard,
        description_similarity=desc_sim,
        name_bonus=name_bonus,
        score=score,
    )


def copy_labels(target: SkillDoc, candidate: SkillDoc) -> list[str]:
    """Classify the copy relationship by normalized hashes (spec section 12)."""
    full_equal = (
        sha256(normalize_for_hash(target.raw))
        == sha256(normalize_for_hash(candidate.raw))
    )
    if full_equal:
        return ["exact-copy"]
    body_equal = (
        sha256(normalize_for_hash(target.body))
        == sha256(normalize_for_hash(candidate.body))
    )
    if body_equal:
        return ["body-copy-with-metadata-change"]
    return []
