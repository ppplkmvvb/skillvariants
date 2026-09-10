"""Real HTTPX transport regressions for source identity and cache freshness."""
import hashlib
import json

import httpx
import pytest

from skillvariants.github import GitHubClient, GitHubError
from skillvariants.parser import GitHubRef, parse_github_url

SHA = "a" * 40


def client_for(tmp_path, monkeypatch, handler):
    monkeypatch.setenv("GITHUB_TOKEN", "test-only-token")
    client = GitHubClient(tmp_path)
    client._http.close()
    client._http = httpx.Client(transport=httpx.MockTransport(handler), headers={"Authorization": "Bearer test-only-token"})
    return client


def test_snapshot_pins_commit_and_preserves_exact_bytes(tmp_path, monkeypatch):
    content = b"---\r\nname: sample\r\n---\r\nAsk first.\r\n"
    def handler(request):
        assert request.headers["Authorization"] == "Bearer test-only-token"
        if "/commits/" in request.url.path:
            return httpx.Response(200, json={"sha": SHA})
        assert request.url.params["ref"] == SHA
        return httpx.Response(200, content=content)
    client = client_for(tmp_path, monkeypatch, handler)
    assert hasattr(client, "fetch_document"), "source metadata needs the production document fetch API"
    doc = client.fetch_document(GitHubRef("a", "b", "main", "SKILL.md"))
    meta = doc.source_metadata
    assert meta["requested_ref"] == "main"
    assert meta["resolved_ref"] == SHA and meta["immutable"] is True
    assert meta["raw_sha256"] == hashlib.sha256(content).hexdigest()
    assert meta["fetched_at"].endswith("Z")
    from pathlib import Path
    assert Path(meta["snapshot_path"]).read_bytes() == content


def test_mutable_cache_refreshes_and_keeps_old_snapshot(tmp_path, monkeypatch):
    version = [0]
    def handler(request):
        if "/commits/" in request.url.path:
            return httpx.Response(200, json={"sha": ("a" if version[0] == 0 else "b") * 40})
        return httpx.Response(200, text=f"version {version[0]}")
    client = client_for(tmp_path, monkeypatch, handler)
    ref = GitHubRef("a", "b", "main", "SKILL.md")
    assert client.fetch_text(ref) == "version 0"
    version[0] = 1
    monkeypatch.setattr("skillvariants.github.time.time", lambda: 9999999999)
    assert client.fetch_text(ref) == "version 1"
    assert len(list((tmp_path / "snapshots").glob("*.md"))) == 2


def test_search_cache_has_bounded_freshness(tmp_path, monkeypatch):
    version = ["old"]
    def handler(request):
        return httpx.Response(200, json={"items": [{"repository": {"full_name": f"a/{version[0]}"}, "path": "SKILL.md"}]})
    client = client_for(tmp_path, monkeypatch, handler)
    assert client.code_search("sample")[0].repo == "a/old"
    version[0] = "new"
    monkeypatch.setattr("skillvariants.github.time.time", lambda: 9999999999)
    client._last_search_at = 0
    assert client.code_search("sample")[0].repo == "a/new"


@pytest.mark.parametrize("operation", ["fetch", "search", "branch"])
def test_network_failures_are_actionable_github_errors(tmp_path, monkeypatch, operation):
    def handler(request):
        raise httpx.ConnectError("offline", request=request)
    client = client_for(tmp_path, monkeypatch, handler)
    with pytest.raises(GitHubError, match="network|Network"):
        if operation == "fetch":
            client.fetch_text(GitHubRef("a", "b", "main", "SKILL.md"))
        elif operation == "search":
            client.code_search("sample")
        else:
            assert hasattr(client, "resolve_default_branch"), "branch resolution must use authenticated client"
            client.resolve_default_branch("a/b")


def test_missing_default_branch_fails_without_guessing_main(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch, lambda request: httpx.Response(200, json={}))
    assert hasattr(client, "resolve_default_branch"), "no guessed default branch"
    with pytest.raises(GitHubError, match="default branch"):
        client.resolve_default_branch("a/b")


def test_unencoded_slash_ref_is_resolved_before_fetch(tmp_path, monkeypatch):
    def handler(request):
        if "/commits/" in request.url.path:
            if request.url.path.endswith("/commits/feature/safe"):
                return httpx.Response(200, json={"sha": SHA})
            return httpx.Response(404)
        assert request.url.path.endswith("/contents/skills/SKILL.md")
        assert request.url.params["ref"] == SHA
        return httpx.Response(200, text="---\nname: sample\n---\nAsk first.")
    client = client_for(tmp_path, monkeypatch, handler)
    ref = parse_github_url("https://github.com/a/b/blob/feature/safe/skills/SKILL.md")
    assert hasattr(client, "fetch_document"), "slash refs must be resolved before fetching"
    doc = client.fetch_document(ref)
    assert doc.source.path == "skills/SKILL.md"
    assert doc.source_metadata["requested_ref"] == "feature/safe"


def test_github_422_missing_commit_prefix_continues_to_real_branch(tmp_path, monkeypatch):
    prefixes = []
    def handler(request):
        if '/commits/' in request.url.path:
            prefix = request.url.path.split('/commits/', 1)[1]
            prefixes.append(prefix)
            if prefix == 'main':
                return httpx.Response(200, json={'sha': SHA})
            return httpx.Response(422, json={'message': f'No commit found for SHA: {prefix}'})
        assert request.url.path.endswith('/contents/skills/systematic-debugging/SKILL.md')
        assert request.url.params['ref'] == SHA
        return httpx.Response(200, text='---\nname: systematic-debugging\n---\nReproduce the error.')
    client = client_for(tmp_path, monkeypatch, handler)
    doc = client.fetch_document(parse_github_url(
        'https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md'))
    assert doc.source.ref == SHA
    assert doc.source.path == 'skills/systematic-debugging/SKILL.md'
    assert prefixes == ['main/skills/systematic-debugging', 'main/skills', 'main']


def test_other_422_commit_errors_are_not_hidden_as_missing_prefixes(tmp_path, monkeypatch):
    calls = []
    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(422, json={'message': 'Validation Failed'})
    client = client_for(tmp_path, monkeypatch, handler)
    with pytest.raises(GitHubError, match='Validation Failed'):
        client.fetch_document(parse_github_url('https://github.com/a/b/blob/main/skills/SKILL.md'))
    assert len(calls) == 1


def test_unresolved_ref_does_not_fetch_or_claim_immutable(tmp_path, monkeypatch):
    def handler(request):
        assert "/commits/" in request.url.path
        return httpx.Response(404)
    client = client_for(tmp_path, monkeypatch, handler)
    with pytest.raises(GitHubError, match="resolve|reference"):
        client.fetch_text(GitHubRef("a", "b", "missing", "SKILL.md"))


def test_offline_cache_exposes_age_without_requiring_credentials(tmp_path, monkeypatch):
    def handler(request):
        if '/commits/' in request.url.path:
            return httpx.Response(200, json={'sha': SHA})
        return httpx.Response(200, text='cached source')
    client = client_for(tmp_path, monkeypatch, handler)
    ref = GitHubRef('a', 'b', 'main', 'SKILL.md')
    client.fetch_text(ref)
    monkeypatch.setattr('skillvariants.github.resolve_token', lambda: None)
    monkeypatch.setattr('skillvariants.github.time.time', lambda: 9999999999)
    offline_client = GitHubClient(tmp_path, offline=True)
    doc = offline_client.fetch_document(ref)
    assert doc.raw == 'cached source'
    assert doc.source_metadata['cache_status'] == 'offline'
    assert doc.source_metadata['stale'] is True


def test_explicit_refresh_updates_fresh_cache(tmp_path, monkeypatch):
    version = [0]
    def handler(request):
        if '/commits/' in request.url.path:
            return httpx.Response(200, json={'sha': ('a' if not version[0] else 'b') * 40})
        return httpx.Response(200, text=str(version[0]))
    client = client_for(tmp_path, monkeypatch, handler)
    ref = GitHubRef('a', 'b', 'main', 'SKILL.md')
    assert client.fetch_text(ref) == '0'
    version[0] = 1
    assert client.fetch_document(ref).source_metadata['cache_status'] == 'hit'
    client.refresh = True
    assert client.fetch_text(ref) == '1'


def test_invalid_utf8_cannot_silently_replace_source_evidence(tmp_path, monkeypatch):
    def handler(request):
        if '/commits/' in request.url.path:
            return httpx.Response(200, json={'sha': SHA})
        return httpx.Response(200, content=b'Ask \xff approval.')
    client = client_for(tmp_path, monkeypatch, handler)
    with pytest.raises(GitHubError, match='UTF-8'):
        client.fetch_text(GitHubRef('a', 'b', 'main', 'SKILL.md'))


def test_snapshot_hash_is_verified_before_cache_reuse(tmp_path, monkeypatch):
    def handler(request):
        if '/commits/' in request.url.path:
            return httpx.Response(200, json={'sha': SHA})
        return httpx.Response(200, text='Ask approval.')
    client = client_for(tmp_path, monkeypatch, handler)
    ref = GitHubRef('a', 'b', 'main', 'SKILL.md')
    doc = client.fetch_document(ref)
    from pathlib import Path
    Path(doc.source_metadata['snapshot_path']).write_bytes(b'Never ask approval.')
    assert client.fetch_text(ref) == 'Ask approval.'


def test_emitted_immutable_ref_reopens_offline_with_original_provenance(tmp_path, monkeypatch):
    def handler(request):
        if '/commits/' in request.url.path:
            return httpx.Response(200, json={'sha': SHA})
        return httpx.Response(200, text='Read the source before editing.')
    client = client_for(tmp_path, monkeypatch, handler)
    original = client.fetch_document(GitHubRef('a', 'b', 'main', 'SKILL.md'))
    offline = GitHubClient(tmp_path, offline=True)
    cached = offline.fetch_document(original.source)
    assert cached.raw == original.raw
    assert cached.source == original.source
    assert cached.source_metadata['requested_ref'] == 'main'
    assert cached.source_metadata['resolved_ref'] == SHA
    assert cached.source_metadata['raw_sha256'] == original.source_metadata['raw_sha256']
    assert cached.source_metadata['fetched_at'] == original.source_metadata['fetched_at']
    assert cached.source_metadata['cache_status'] == 'offline'


def test_branch_refresh_preserves_both_immutable_snapshot_aliases(tmp_path, monkeypatch):
    version = [0]
    def handler(request):
        if '/commits/' in request.url.path:
            return httpx.Response(200, json={'sha': ('a' if not version[0] else 'b') * 40})
        return httpx.Response(200, text=f'Version {version[0]}')
    client = client_for(tmp_path, monkeypatch, handler)
    ref = GitHubRef('a', 'b', 'main', 'SKILL.md')
    old = client.fetch_document(ref)
    version[0] = 1
    client.refresh = True
    new = client.fetch_document(ref)
    offline = GitHubClient(tmp_path, offline=True)
    assert offline.fetch_document(old.source).raw == 'Version 0'
    assert offline.fetch_document(new.source).raw == 'Version 1'
    assert old.source.ref != new.source.ref
    assert old.source_metadata['snapshot_path'] != new.source_metadata['snapshot_path']
