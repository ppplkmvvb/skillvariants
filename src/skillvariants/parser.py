"""URL and SKILL.md parsing for the skillvariants spike.

Only deterministic parsing lives here: GitHub file URL -> GitHubRef, and
raw SKILL.md text -> SkillDoc (YAML frontmatter + body).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import unquote, urlsplit

import yaml


@dataclass(frozen=True)
class GitHubRef:
    owner: str
    repo: str
    ref: str
    path: str

    @property
    def repo_slug(self) -> str:
        return f"{self.owner}/{self.repo}"

    @property
    def slug(self) -> str:
        return f"{self.repo_slug}/{self.path}"

    @property
    def raw_url(self) -> str:
        return (
            f"https://raw.githubusercontent.com/"
            f"{self.owner}/{self.repo}/{self.ref}/{self.path}"
        )

    @property
    def api_contents_url(self) -> str:
        return (
            f"https://api.github.com/repos/{self.owner}/{self.repo}/"
            f"contents/{self.path}?ref={self.ref}"
        )


_BLOB_URL_RE = re.compile(
    r"^(?P<host>github\.com)/(?P<owner>[^/]+)/(?P<repo>[^/]+)/"
    r"(blob|raw|resolve)/(?P<ref>[^/]+)/(?P<path>.+)$"
)
_RAW_URL_RE = re.compile(
    r"^(?P<host>raw\.githubusercontent\.com)/(?P<owner>[^/]+)/"
    r"(?P<repo>[^/]+)/(?P<ref>[^/]+)/(?P<path>.+)$"
)


def parse_github_url(url: str) -> GitHubRef:
    """Parse a GitHub blob/raw URL into a GitHubRef.

    Supported forms:
      https://github.com/OWNER/REPO/blob/REF/PATH
      https://github.com/OWNER/REPO/raw/REF/PATH
      https://github.com/OWNER/REPO/resolve/REF/PATH
      https://raw.githubusercontent.com/OWNER/REPO/REF/PATH

    Raises ValueError with an actionable message otherwise.
    """
    url = url.strip()
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ValueError(
            f"Not a valid GitHub URL: {url!r}. Expected an https URL."
        )
    host = parts.netloc.lower()
    path = unquote(parts.path).lstrip("/")
    candidate = f"{host}/{path}"

    for pattern in (_BLOB_URL_RE, _RAW_URL_RE):
        match = pattern.match(candidate)
        if match:
            return GitHubRef(
                owner=match["owner"],
                repo=match["repo"],
                ref=match["ref"],
                path=match["path"],
            )

    raise ValueError(
        f"Could not parse GitHub file URL: {url!r}. "
        "Expected https://github.com/OWNER/REPO/blob/REF/PATH or "
        "https://raw.githubusercontent.com/OWNER/REPO/REF/PATH"
    )


@dataclass
class SkillDoc:
    frontmatter: dict
    body: str
    raw: str
    source: GitHubRef | None = None
    parse_errors: list[str] = field(default_factory=list)

    @property
    def name(self) -> str | None:
        value = self.frontmatter.get("name")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @property
    def description(self) -> str | None:
        value = self.frontmatter.get("description")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @property
    def canonical_ref(self) -> str | None:
        for key in (
            "canonical_skill",
            "canonical",
            "canonical_path",
            "canonical-path",
            "points_to",
            "redirect_to",
        ):
            value = self.frontmatter.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None


def split_frontmatter(text: str) -> tuple[dict, str, bool, list[str]]:
    """Return (frontmatter_dict, body, had_frontmatter, errors).

    Robust to missing frontmatter, unterminated frontmatter, and YAML errors.
    """
    text = text.removeprefix("\ufeff")
    if not text.lstrip().startswith("---"):
        return {}, text, False, []

    # Keep indentation-sensitive leading spaces out of the way: opening '---'
    # is the first non-space line in every real SKILL.md.
    sep_line = text.index("---")  # first occurrence is the opener
    lines = text[sep_line:].splitlines()
    end: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = index
            break
    if end is None:
        return {}, text, False, [
            "unterminated frontmatter: closing '---' not found"
        ]

    fm_text = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    errors: list[str] = []
    try:
        data = yaml.safe_load(fm_text)
    except yaml.YAMLError as exc:
        return {}, body, True, [f"frontmatter failed to parse: {exc}"]
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return {}, body, True, ["frontmatter YAML is not a mapping"]
    return data, body, True, errors


def parse_skill_md(text: str, source: GitHubRef | None = None) -> SkillDoc:
    frontmatter, body, _had, errors = split_frontmatter(text)
    return SkillDoc(
        frontmatter=frontmatter,
        body=body,
        raw=text,
        source=source,
        parse_errors=errors,
    )
