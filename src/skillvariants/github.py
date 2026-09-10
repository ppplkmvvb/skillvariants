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
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import httpx

from .parser import GitHubRef, SkillDoc, parse_skill_md

AUTH_REQUIRED_MESSAGE = (
    "GitHub Code Search requires authentication.\n"
    "Set GITHUB_TOKEN or authenticate with `gh auth login`."
)
SEARCH_PER_PAGE = 100
SEARCH_MIN_INTERVAL = 2.15  # 30 req/min allowance with a small margin
CACHE_MAX_AGE_SECONDS = 3600


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
    def __init__(self, cache_dir: Path, timeout: float = 30.0, *,
                 max_age_seconds: float = CACHE_MAX_AGE_SECONDS,
                 refresh: bool = False, offline: bool = False) -> None:
        token = None if offline else resolve_token()
        if not token and not offline:
            raise AuthError(AUTH_REQUIRED_MESSAGE)
        self.token = token
        self.cache_dir = Path(cache_dir)
        self.max_age_seconds = max(0, max_age_seconds)
        self.refresh = refresh
        self.offline = offline
        self.search_metadata: dict = {}
        self._http = httpx.Client(
            headers={"Authorization": f"Bearer {token}"} if token else {},
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
        """Compatibility API; use fetch_document to retain snapshot metadata."""
        return self.fetch_document(ref).raw

    def _get(self, url: str, **kwargs) -> httpx.Response:
        if self.offline:
            raise GitHubError("Offline cache miss; reconnect and refresh this source.")
        try:
            return self._http.get(url, **kwargs)
        except httpx.HTTPError as exc:
            raise GitHubError(f"GitHub network failure ({type(exc).__name__}); check connectivity and retry.") from exc

    @staticmethod
    def _json(response: httpx.Response) -> dict:
        try:
            result = response.json()
        except ValueError as exc:
            raise GitHubError("GitHub returned invalid JSON; retry the request.") from exc
        if not isinstance(result, dict):
            raise GitHubError("GitHub returned an unexpected response shape.")
        return result

    def resolve_default_branch(self, repo_slug: str) -> str:
        response = self._get(f"https://api.github.com/repos/{repo_slug}")
        self._raise_for_status(response, context=f"resolving default branch for {repo_slug}")
        branch = self._json(response).get("default_branch")
        if not isinstance(branch, str) or not branch.strip():
            raise GitHubError(f"Cannot resolve default branch for {repo_slug}; provide an explicit ref.")
        return branch

    def _resolve_source(self, ref: GitHubRef) -> tuple[GitHubRef, str]:
        requested = ref.ref or self.resolve_default_branch(ref.repo_slug)
        candidates = [(requested, ref.path)]
        if ref.url_tail and not re.fullmatch(r"[0-9a-fA-F]{40}", requested):
            parts = ref.url_tail.split("/")
            if len(parts) > 24:
                raise GitHubError("URL ref/path is ambiguous; percent-encode slashes in the ref or use a commit SHA.")
            candidates = [("/".join(parts[:i]), "/".join(parts[i:]))
                          for i in range(len(parts) - 1, 0, -1)]
        for requested, path in candidates:
            if re.fullmatch(r"[0-9a-fA-F]{40}", requested):
                return GitHubRef(ref.owner, ref.repo, requested.lower(), path), requested
            response = self._get(
                f"https://api.github.com/repos/{ref.repo_slug}/commits/{quote(requested, safe='')}"
            )
            if response.status_code == 404:
                continue
            if (response.status_code == 422
                    and self._json(response).get("message") == f"No commit found for SHA: {requested}"):
                # GitHub uses this specific 422 for non-existent ref/path
                # prefixes. Other validation and rate errors remain failures.
                continue
            self._raise_for_status(response, context=f"resolving reference {requested!r} for {ref.repo_slug}")
            commit = self._json(response).get("sha")
            if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
                raise GitHubError(f"Cannot resolve immutable reference for {ref.repo_slug}@{requested}.")
            return GitHubRef(ref.owner, ref.repo, commit.lower(), path), requested
        raise GitHubError(f"Cannot resolve reference {ref.ref!r} for {ref.repo_slug}; check the ref/path or use a commit SHA.")

    def resolve_ref(self, ref: GitHubRef) -> GitHubRef:
        return self._resolve_source(ref)[0]

    def _read_cache(self, path: Path) -> dict | None:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    def _is_fresh(self, value: dict) -> bool:
        epoch = value.get("fetched_epoch")
        return (not self.refresh and isinstance(epoch, (int, float))
                and 0 <= time.time() - epoch < self.max_age_seconds)

    @staticmethod
    def _decode_source(raw_bytes: bytes) -> str:
        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise GitHubError("Source is not valid UTF-8; cannot produce trustworthy text evidence from replacement characters.") from exc

    def fetch_document(self, ref: GitHubRef) -> SkillDoc:
        index_path = self._file_cache_path(ref).with_suffix(".json")
        cached = self._read_cache(index_path)
        immutable_input = bool(re.fullmatch(r"[0-9a-fA-F]{40}", ref.ref))
        if cached and (self.offline or self._is_fresh(cached) or (immutable_input and not self.refresh)):
            metadata = dict(cached.get("source", {}))
            digest = metadata.get("raw_sha256", "")
            if re.fullmatch(r"[0-9a-f]{64}", digest):
                snapshot_path = self.cache_dir / "snapshots" / f"{digest}.md"
                if snapshot_path.exists():
                    raw_bytes = snapshot_path.read_bytes()
                    if hashlib.sha256(raw_bytes).hexdigest() == digest:
                        metadata["snapshot_path"] = str(snapshot_path.resolve())
                        metadata["cache_status"] = ("offline" if self.offline else "hit")
                        metadata["stale"] = not immutable_input and not self._is_fresh(cached)
                        resolved = GitHubRef(ref.owner, ref.repo, metadata["resolved_ref"], metadata["path"])
                        doc = parse_skill_md(self._decode_source(raw_bytes), source=resolved)
                        doc.source_metadata = metadata
                        return doc
        resolved, requested = self._resolve_source(ref)
        response = self._get(
            resolved.api_contents_url,
            headers={"Accept": "application/vnd.github.raw"},
        )
        self._raise_for_status(response, context=f"fetching {resolved.slug}")
        raw_bytes = response.content
        digest = hashlib.sha256(raw_bytes).hexdigest()
        snapshot_path = self.cache_dir / "snapshots" / f"{digest}.md"
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_bytes(raw_bytes)
        epoch = time.time()
        metadata = {
            "kind": "github", "repository": resolved.repo_slug, "path": resolved.path,
            "requested_ref": requested, "resolved_ref": resolved.ref, "immutable": True,
            "raw_sha256": digest,
            "fetched_at": datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace("+00:00", "Z"),
            "snapshot_path": str(snapshot_path.resolve()), "cache_status": "network", "stale": False,
        }
        index_path.parent.mkdir(parents=True, exist_ok=True)
        cache_record = json.dumps({"fetched_epoch": epoch, "source": metadata})
        index_path.write_text(cache_record, encoding="utf-8")
        # Public source URLs use the resolved commit, so make that exact source
        # available offline while retaining the original fetch provenance.
        immutable_index_path = self._file_cache_path(resolved).with_suffix(".json")
        if immutable_index_path != index_path:
            immutable_index_path.write_text(cache_record, encoding="utf-8")
        doc = parse_skill_md(self._decode_source(raw_bytes), source=resolved)
        doc.source_metadata = metadata
        return doc

    # ---- code search ----------------------------------------------------
    def code_search(self, query: str, max_pages: int = 3) -> list[CodeHit]:
        cache_path = self._search_cache_path(query, max_pages)
        cached = self._read_cache(cache_path)
        if cached and (self.offline or self._is_fresh(cached)):
            self.search_metadata = {"cache_status": "offline" if self.offline else "hit",
                                    "fetched_at": cached.get("fetched_at"),
                                    "stale": not self._is_fresh(cached)}
            return [CodeHit(**item) for item in cached["items"]]

        hits: list[CodeHit] = []
        for page in range(1, max_pages + 1):
            self._throttle_search()
            response = self._get(
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
            payload = self._json(response)
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
        epoch = time.time()
        fetched_at = datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace("+00:00", "Z")
        self.search_metadata = {"cache_status": "network", "fetched_at": fetched_at, "stale": False}
        cache_path.write_text(
            json.dumps({"fetched_epoch": epoch, "fetched_at": fetched_at,
                        "items": [hit.__dict__ for hit in hits]}, indent=1),
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
