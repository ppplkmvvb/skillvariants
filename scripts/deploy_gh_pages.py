"""Explicit manual gh-pages deployment; needs repository contents:write only.

This updates the branch, not Pages settings. Configure Pages once to serve
gh-pages at /. Importing this module performs no I/O or deployment.
"""
from __future__ import annotations

import argparse
import base64
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"


class ApiError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def make_api(repository: str):
    import httpx
    from skillvariants.github import resolve_token

    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("repository must be OWNER/REPO")
    token = resolve_token()
    if not token:
        raise ValueError("Set GITHUB_TOKEN or run gh auth login")

    def api(endpoint: str, method: str = "GET", body: dict | None = None):
        try:
            with httpx.Client(timeout=60, follow_redirects=False) as client:
                response = client.request(method, f"https://api.github.com/repos/{repository}/{endpoint}",
                                          headers={"Authorization": f"Bearer {token}",
                                                   "Accept": "application/vnd.github+json"}, json=body)
        except httpx.RequestError:
            raise ApiError(0, f"Network failure during {method} {endpoint}") from None
        if not 200 <= response.status_code < 300:
            raise ApiError(response.status_code, f"GitHub {method} {endpoint}: HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError:
            raise ApiError(response.status_code, f"GitHub {method} {endpoint}: invalid JSON response") from None
    return api


def deploy(web_dir: Path, api) -> str:
    web_dir = web_dir.resolve()
    if not (web_dir / "index.html").is_file():
        raise ValueError("web directory must contain index.html")
    files = []
    for path in sorted(web_dir.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"web directory contains symlink: {path.name}")
        if path.is_file():
            rel = path.relative_to(web_dir).as_posix()
            if any(part.startswith(".") for part in path.relative_to(web_dir).parts):
                raise ValueError(f"web directory contains hidden file: {rel}")
            files.append((rel, path.read_bytes()))
    try:
        parent = api("git/refs/heads/gh-pages")["object"]["sha"]
    except ApiError as exc:
        if exc.status != 404:
            raise
        parent = None
    tree_items = []
    for rel, content in files:
        sha = api("git/blobs", "POST", {"content": base64.b64encode(content).decode("ascii"), "encoding": "base64"})["sha"]
        tree_items.append({"path": rel, "mode": "100644", "type": "blob", "sha": sha})
    tree = api("git/trees", "POST", {"tree": tree_items})["sha"]
    commit = api("git/commits", "POST", {"message": "Publish verified SkillVariants explorer", "tree": tree,
                                          "parents": [parent] if parent else []})["sha"]
    if parent:
        api("git/refs/heads/gh-pages", "PATCH", {"sha": commit, "force": False})
    else:
        api("git/refs", "POST", {"ref": "refs/heads/gh-pages", "sha": commit})
    return commit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="ppplkmvvb/skillvariants")
    parser.add_argument("--web-dir", type=Path, default=WEB)
    args = parser.parse_args(argv)
    try:
        commit = deploy(args.web_dir, make_api(args.repository))
    except (OSError, ValueError, ApiError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"gh-pages updated to {commit}; Pages must be configured to serve this branch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
