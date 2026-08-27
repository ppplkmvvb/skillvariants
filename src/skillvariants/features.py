"""Deterministic structural feature extraction for SKILL.md documents.

Every feature here is derived by plain string/regex rules; nothing semantic.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .parser import SkillDoc

# Common shell/tool commands reported as "command-related instructions".
KNOWN_COMMANDS: tuple[str, ...] = (
    "npm", "npx", "pnpm", "yarn", "bun", "pip", "pipx", "uv", "pytest",
    "python", "node", "cargo", "go", "git", "gh", "curl", "wget", "docker",
    "make", "bash", "sh", "powershell",
)

# Phrases that indicate a routing boundary between skills.
ROUTING_PHRASES: tuple[str, ...] = (
    "routing boundary",
    "related skills",
    "do not use",
    "don't use",
    "route to",
    "use x instead",
    "owns",
)
ROUTING_HEADINGS: tuple[str, ...] = (
    "routing boundary",
    "related skills",
    "related skills and workflows",
)

# Phrases that indicate a compatibility wrapper around a canonical skill.
WRAPPER_PHRASES: tuple[str, ...] = (
    "canonical definition",
    "resolve canonical path",
    "compatibility wrapper",
    "project-facing entry",
    "canonical skill",
)
WRAPPER_FRONTMATTER_KEYS: tuple[str, ...] = (
    "canonical_skill",
    "canonical",
    "canonical_path",
    "canonical-path",
    "points_to",
    "redirect_to",
)

# Conservative project-specialization signals (phrase queries only).
PROJECT_PHRASES: tuple[str, ...] = (
    "this project",
    "this repository",
    "our project",
    "project-specific",
    "migration note",
    "migration notes",
    "legacy",
    "planning mode",
)
_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_URL_RE = re.compile(r"https?://[^\s)>\"'`]+")
_MD_REF_RE = re.compile(r"[\w./@-]+\.md(?:\#[\w-]+)?")
_PATH_REF_RE = re.compile(r"([\w./-]+)(?:/)?(?:scripts|references|assets)/[^\s)`]*")
_SKILL_REF_RE = re.compile(r"\b([a-z][a-z0-9-]{2,})\s+skill\b", re.IGNORECASE)
_SKILL_REF_STOPWORDS = {
    "this", "the", "your", "that", "these", "those", "any", "other",
    "one", "each", "some", "every", "own", "more", "all", "two",
}
# Placeholder/template markers: documents dense with these are skeletons,
# not adaptations. Used to down-rank representatives (production fix).
PLACEHOLDER_PATTERNS: tuple[str, ...] = (
    r"\[describe[^\]]*\]",
    r"\[add step[^\]]*\]",
    r"\[insert[^\]]*\]",
    r"\[todo\]",
    r"<todo>",
    r"(?<![a-z])todo:",
    r"\btbd\b",
    r"\byour_[a-z0-9_]+\b",
    r"replace[_ ]me",
    r"lorem ipsum",
)
_PLACEHOLDER_RE = re.compile("|".join(PLACEHOLDER_PATTERNS), re.IGNORECASE)

_TABLE_SEP_RE = re.compile(r"^\s*\|(?:\s*:?-+:?\s*\|)+\s*$")
_ALL_CAPS_RE = re.compile(r"\b[A-Z][A-Z ,'\"-]{5,}[A-Z]\b")
_PROJECT_PHRASE_RE = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in PROJECT_PHRASES) + r")\b",
    re.IGNORECASE,
)


@dataclass
class SkillFeatures:
    n_lines: int = 0
    n_chars: int = 0
    headings: list[str] = field(default_factory=list)
    n_code_blocks: int = 0
    n_tables: int = 0
    n_bullets: int = 0
    commands: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    md_refs: list[str] = field(default_factory=list)
    path_refs: list[str] = field(default_factory=list)
    cross_skill_refs: list[str] = field(default_factory=list)
    routing_signals: list[str] = field(default_factory=list)
    wrapper_signals: list[str] = field(default_factory=list)
    canonical_ref: str | None = None
    is_wrapper: bool = False
    n_placeholder_hits: int = 0
    placeholder_signal: float = 0.0


def _unique_sorted(values: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for value in values:
        seen.setdefault(value.strip(), None)
    return sorted(seen)


def extract_features(doc: SkillDoc) -> SkillFeatures:
    body = doc.body
    body_lower = body.lower()
    features = SkillFeatures(
        n_lines=len(body.splitlines()),
        n_chars=len(body),
        canonical_ref=doc.canonical_ref,
    )

    for line in body.splitlines():
        heading = _HEADING_RE.match(line)
        if heading:
            features.headings.append(heading.group(2).strip())
        if _BULLET_RE.match(line):
            features.n_bullets += 1
        if _TABLE_SEP_RE.match(line):
            features.n_tables += 1

    features.n_code_blocks = body.count("```") // 2

    commands = [
        cmd
        for cmd in KNOWN_COMMANDS
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(cmd)}(?!\w)", body_lower)
    ]
    features.commands = commands

    features.urls = _unique_sorted(_URL_RE.findall(body))
    features.md_refs = _unique_sorted(
        match.group(0) for match in _MD_REF_RE.finditer(body)
    )
    features.path_refs = _unique_sorted(
        match.group(0) for match in _PATH_REF_RE.finditer(body)
    )
    features.cross_skill_refs = _unique_sorted(
        match.group(1).lower()
        for match in _SKILL_REF_RE.finditer(body_lower)
        if match.group(1).lower() not in _SKILL_REF_STOPWORDS
    ) + _unique_sorted(
        match.group(0) for match in re.finditer(r"skills/[a-z0-9-]+", body_lower)
    )
    features.cross_skill_refs = _unique_sorted(features.cross_skill_refs)

    routing: list[str] = []
    for phrase in ROUTING_PHRASES:
        if phrase in body_lower:
            routing.append(phrase)
    for heading in features.headings:
        if heading.lower() in ROUTING_HEADINGS:
            routing.append(f"heading: {heading}")
    features.routing_signals = _unique_sorted(routing)

    wrapper: list[str] = []
    for phrase in WRAPPER_PHRASES:
        if phrase in body_lower:
            wrapper.append(phrase)
    for key in WRAPPER_FRONTMATTER_KEYS:
        if key in doc.frontmatter:
            wrapper.append(f"frontmatter: {key}")
    features.wrapper_signals = _unique_sorted(wrapper)

    short_document = features.n_lines <= 40
    has_canonical = features.canonical_ref is not None
    features.is_wrapper = short_document and (
        has_canonical or len(features.wrapper_signals) >= 2
    )

    hits = _PLACEHOLDER_RE.findall(body)
    features.n_placeholder_hits = len(hits)
    # >=1 marker per ~4 lines saturates the signal; honest rewrites score 0.
    features.placeholder_signal = min(
        len(hits) * 4.0 / max(features.n_lines, 1), 1.0
    )
    return features


def uppercase_rules(text: str) -> list[str]:
    """Distinctive ALL-CAPS sentences, used for preserved/added/removed rules."""
    lines = [line.strip() for line in text.splitlines()]
    rules: list[str] = []
    for line in lines:
        if _ALL_CAPS_RE.fullmatch(line) and len(line) >= 12:
            rules.append(line)
    return _unique_sorted(rules)
