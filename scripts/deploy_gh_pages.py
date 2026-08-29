"""Deploy web/ to gh-pages via the GitHub API (git push is unreliable here)."""
from __future__ import annotations

import base64
import json
import subprocess
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
OWNER, REPO = "ppplkmvvb", "skillvariants"


def api(endpoint: str, method: str = "GET", body: dict | None = None):
    import httpx
    token = subprocess.run(["gh", "auth", "token"], capture_output=True,
                           text=True).stdout.strip()
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/vnd.github+json"}
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/{endpoint}"
    with httpx.Client(timeout=120) as client:
        if method == "GET":
            r = client.get(url, headers=headers)
        else:
            r = client.request(method, url, headers=headers, json=body)
    if r.status_code >= 300:
        raise RuntimeError(f"{method} {endpoint}: {r.status_code} {r.text[:200]}")
    return r.json() if r.text.strip() else {}


def blob(path: Path) -> str:
    content = base64.b64encode(path.read_bytes()).decode()
    sha = api("git/blobs", "POST",
              {"content": content, "encoding": "base64"})["sha"]
    print(f"  blob {path.name} -> {sha[:10]} ({path.stat().st_size} bytes)")
    return sha


def main() -> None:
    files = {}
    for path in sorted(WEB.rglob("*")):
        if path.is_file():
            rel = path.relative_to(WEB).as_posix()
            files[rel] = blob(path)
            print("blob:", rel)

    tree_items = [
        {"path": rel, "mode": "100644", "type": "blob", "sha": sha}
        for rel, sha in files.items()
    ]
    head = api("git/refs/heads/main")
    base_commit = api(f"git/commits/{head['object']['sha']}")
    base_tree = api(f"git/commits/{head['object']['sha']}")["tree"]["sha"]
    tree = api("git/trees", "POST",
               {"base_tree": base_tree, "tree": tree_items})["sha"]
    commit = api("git/commits", "POST", {
        "message": "web explorer (v0.2.0 data)",
        "tree": tree,
        "parents": [base_commit["sha"]],
    })["sha"]

    try:
        api("git/refs/heads/gh-pages", "POST", {"sha": commit, "force": True})
    except RuntimeError:
        api("git/refs", "POST", {"ref": "refs/heads/gh-pages", "sha": commit})
    print("gh-pages updated to", commit[:10])

    try:
        api("pages", "POST", {"source": {"branch": "gh-pages", "path": "/"}})
        print("pages site created (branch gh-pages, path /)")
    except RuntimeError as exc:
        if "already exists" in str(exc) or "422" in str(exc):
            print("pages site already configured")
        else:
            print("pages config:", exc)


if __name__ == "__main__":
    main()
