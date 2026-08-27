"""Minimal authenticated GitHub access with a filesystem cache.

Access priority (spec section 8):
  GITHUB_TOKEN / GH_TOKEN environment variable
      -> GitHub REST API over httpx
  otherwise an authenticated `gh` CLI (token read via `gh auth token`)
      -> same REST client
  otherwise a clear, actionable failure.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from .parser import GitHubRef

AUTH_REQUIRED_MESSAGE = (
    "GitHub Code Search requires authentication.\n"
    "Set GITHUB_TOKEN or authenticate with `gh auth login`."
)
SEARCH_PER_PAGE = 100
SEARCH_MIN_INTERVAL = 2.15  # 30 req/min allowance with a small margin


class GitHubError(RuntimeError):
    """Actionable GitHub/network failure."""


class AuthError(GitHubError):
    pass


@dataclass(frozen=True)
class CodeHit:
    repo: str  # owner/repo
    path: str
    default_branch: str
    sha: str
    api_url: str

    def to_ref(self) -> GitHubRef:
        owner, repo = self.repo.split("/", 1)
        return GitHubRef(owner=owner, repo=repo, ref=self.default_branch, path=self.path)


def resolve_token() -> str | None:
    env_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if env_token and env_token.strip():
        return env_token.strip()
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


class GitHubClient:
    def __init__(self, cache_dir: Path, timeout: float = 30.0) -> None:
        token = resolve_token()
        if not token:
            raise AuthError(AUTH_REQUIRED_MESSAGE)
        self.token = token
        self.cache_dir = cache_dir
        self._http = httpx.Client(
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
            follow_redirects=True,
        )
        self._last_search_at = 0.0

    # ---- cache helpers -------------------------------------------------
    def _file_cache_path(self, ref: GitHubRef) -> Path:
        key = hashlib.sha1(f"{ref.slug}@{ref.ref}".encode("utf-8")).hexdigest()
        return self.cache_dir / "files" / f"{key}.md"

    def _search_cache_path(self, query: str, max_pages: int) -> Path:
        key = hashlib.sha1(query.encode("utf-8")).hexdigest()
        return self.cache_dir / "search" / f"{key}-p{max_pages}.json"

    # ---- file fetching --------------------------------------------------
    def fetch_text(self, ref: GitHubRef) -> str:
        path = self._file_cache_path(ref)
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
        response = self._http.get(
            ref.api_contents_url,
            headers={"Accept": "application/vnd.github.raw"},
        )
        self._raise_for_status(response, context=f"fetching {ref.slug}")
        text = response.text
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return text

    # ---- code search ----------------------------------------------------
    def code_search(self, query: str, max_pages: int = 3) -> list[CodeHit]:
        cache_path = self._search_cache_path(query, max_pages)
        if cache_path.exists():
            raw = json.loads(cache_path.read_text(encoding="utf-8"))
            return [CodeHit(**item) for item in raw]

        hits: list[CodeHit] = []
        for page in range(1, max_pages + 1):
            self._throttle_search()
            response = self._http.get(
                "https://api.github.com/search/code",
                params={
                    "q": query,
                    "per_page": SEARCH_PER_PAGE,
                    "page": page,
                },
                headers={"Accept": "application/vnd.github+json"},
            )
            if response.status_code in (401, 403) and "rate limit" in response.text.lower():
                raise GitHubError(
                    "GitHub code search rate limit hit. "
                    f"Response: {response.text[:300]}"
                )
            if response.status_code in (401, 403, 422):
                raise AuthError(
                    f"{AUTH_REQUIRED_MESSAGE}\n"
                    f"GitHub returned {response.status_code}: "
                    f"{response.text[:300]}"
                )
            self._raise_for_status(response, context=f"code search {query!r}")
            payload = response.json()
            items = payload.get("items", [])
            for item in items:
                repo = item.get("repository", {})
                hits.append(
                    CodeHit(
                        repo=repo.get("full_name", ""),
                        path=item.get("path", ""),
                        default_branch=repo.get("default_branch", ""),
                        sha=item.get("sha", ""),
                        api_url=item.get("url", ""),
                    )
                )
            if len(items) < SEARCH_PER_PAGE:
                break

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps([hit.__dict__ for hit in hits], indent=1),
            encoding="utf-8",
        )
        return hits

    # ---- internals ------------------------------------------------------
    def _throttle_search(self) -> None:
        elapsed = time.monotonic() - self._last_search_at
        if elapsed < SEARCH_MIN_INTERVAL:
            time.sleep(SEARCH_MIN_INTERVAL - elapsed)
        self._last_search_at = time.monotonic()

    @staticmethod
    def _raise_for_status(response: httpx.Response, context: str) -> None:
        if response.status_code == 404:
            raise GitHubError(f"Not found while {context} (HTTP 404)")
        if response.status_code == 403:
            raise GitHubError(
                f"Rate limit or permission problem while {context} (HTTP 403): "
                f"{response.text[:200]}"
            )
        if response.status_code >= 400:
            raise GitHubError(
                f"GitHub API error {response.status_code} while {context}: "
                f"{response.text[:200]}"
            )
