"""Shared test utilities: a fake GitHub client so the whole related-pipeline
runs offline against local fixtures."""
from __future__ import annotations

from pathlib import Path

import pytest

from skillvariants.github import CodeHit
from skillvariants.parser import GitHubRef

FIXTURES = Path(__file__).parent / "fixtures"

SUPERPOWERS_SD = ("obra/superpowers", "skills/systematic-debugging/SKILL.md", "main")
LOOPKIT_SD = ("Archive228/loopkit", "skills/systematic-debugging/SKILL.md", "main")
VIBESKILLS_SD = (
    "foryourhealth111-pixel/Vibe-Skills",
    "bundled/skills/systematic-debugging/SKILL.md",
    "main",
)


def fixture_text(rel: str) -> str:
    return (FIXTURES / rel).read_text(encoding="utf-8")


class FakeGitHubClient:
    """Offline stand-in for skillvariants.github.GitHubClient."""

    def __init__(self, files: dict[tuple[str, str, str], str], hits: list[CodeHit]):
        self._files = files
        self._hits = hits

    def fetch_text(self, ref: GitHubRef) -> str:
        key = (ref.repo_slug if hasattr(ref, "repo_slug") else f"{ref.owner}/{ref.repo}",
               ref.path, ref.ref)
        try:
            return self._files[key]
        except KeyError:
            raise FileNotFoundError(key)

    def code_search(self, query: str, max_pages: int = 3) -> list[CodeHit]:
        assert query, "query required"
        return list(self._hits)


@pytest.fixture
def debugging_fake_client() -> FakeGitHubClient:
    files = {
        SUPERPOWERS_SD: fixture_text("systematic_debugging/reference_superpowers.md"),
        LOOPKIT_SD: fixture_text("systematic_debugging/variant_loopkit.md"),
        VIBESKILLS_SD: fixture_text("systematic_debugging/variant_vibeskills.md"),
    }
    hits = [
        CodeHit(repo=LOOPKIT_SD[0], path=LOOPKIT_SD[1],
                default_branch=LOOPKIT_SD[2], sha="", api_url=""),
        CodeHit(repo=VIBESKILLS_SD[0], path=VIBESKILLS_SD[1],
                default_branch=VIBESKILLS_SD[2], sha="", api_url=""),
    ]
    return FakeGitHubClient(files=files, hits=hits)
