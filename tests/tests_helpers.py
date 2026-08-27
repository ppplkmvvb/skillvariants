"""Shared synthetic-skill builders for offline pipeline tests."""
from __future__ import annotations

from skillvariants.cli import _build_variant_pool
from skillvariants.github import CodeHit

from conftest import FakeGitHubClient

TARGET_URL = "https://github.com/test/target/blob/main/skills/sample/SKILL.md"

# Live URLs of the three validation families + known variant anchors. Used by
# optional live checks and regression pins; offline tests never fetch these.
LIVE_REFERENCE_URLS = {
    "frontend-design": (
        "https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md"
    ),
    "systematic-debugging": (
        "https://github.com/obra/superpowers/blob/main/"
        "skills/systematic-debugging/SKILL.md"
    ),
    "brainstorming": (
        "https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md"
    ),
}

LIVE_VARIANT_URLS = {
    # NOTE: Rain120/qq-music-api's default branch is `next`, not `main`.
    "frontend-design": (
        "https://github.com/Rain120/qq-music-api/blob/next/"
        "skills/frontend-design/SKILL.md"
    ),
    "systematic-debugging": (
        "https://github.com/Archive228/loopkit/blob/main/"
        "skills/systematic-debugging/SKILL.md"
    ),
    "brainstorming": (
        "https://github.com/derHaken/SuperAntigravity/blob/main/"
        "skills/brainstorming/SKILL.md"
    ),
}


TARGET_BODY = """# Sample
## Overview
Do the work carefully before changing anything.
## Phase 1: investigate
Read the failing output and reproduce it first.
## Phase 2: implement
Write the fix with a regression test.
## Phase 3: verify
Run git commands to verify everything passes.
"""


def doc_text(
    body: str,
    name: str = "sample",
    description: str = "A sample skill guiding careful systematic work.",
    extra_fm: str = "",
) -> str:
    return f"---\nname: {name}\ndescription: {description}{extra_fm}\n---\n{body}"


def build_test_pool(rows: dict[tuple[str, str], str]):
    """Builds a variant pool against the TARGET_URL using a fake client."""
    files = {("test/target", "skills/sample/SKILL.md", "main"): doc_text(TARGET_BODY)}
    files.update({(repo, path, "main"): text for (repo, path), text in rows.items()})
    hits = [
        CodeHit(repo=repo, path=path, default_branch="main", sha="", api_url="")
        for repo, path in rows
    ]
    client = FakeGitHubClient(files=files, hits=hits)
    return _build_variant_pool(TARGET_URL, cache_dir=None, max_pages=1, client=client)
