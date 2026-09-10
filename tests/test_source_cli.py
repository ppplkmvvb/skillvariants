"""Freshness policy must reach real Typer entry points without global state."""
from __future__ import annotations

import json

import httpx
import pytest
from typer.testing import CliRunner

from skillvariants import cli, cli_helpers
from skillvariants.github import GitHubClient
from skillvariants.parser import parse_github_url

URL = 'https://github.com/example/skills/blob/main/SKILL.md'
RAW = '---\nname: source-demo\n---\nAsk for approval before deployment.\n'
COMMIT = 'd' * 40
runner = CliRunner()


class FakeClient:
    def fetch_text(self, ref):
        return RAW

    def code_search(self, query, max_pages=3):
        return []


@pytest.mark.parametrize('command', ['inspect', 'compare', 'related', 'evidence', 'study-start'])
@pytest.mark.parametrize('flags,expected', [
    (['--refresh', '--cache-max-age', '20'], {'refresh': True, 'max_age_seconds': 20}),
    (['--offline', '--cache-max-age', '0'], {'offline': True, 'max_age_seconds': 0}),
])
def test_global_cache_flags_reach_every_retrieval_command(tmp_path, monkeypatch, command, flags, expected):
    calls = []
    def factory(**kwargs):
        calls.append(kwargs)
        return FakeClient()
    monkeypatch.setattr(cli, 'GitHubClient', factory)
    monkeypatch.setattr(cli_helpers, 'GitHubClient', factory)
    args = [*flags, command, URL]
    if command == 'compare':
        args.append(URL)
    if command == 'study-start':
        args.extend(['--base-dir', str(tmp_path / 'workspace')])
    args.extend(['--cache-dir', str(tmp_path / 'cache'), '--json'])
    result = runner.invoke(cli.app, args)
    assert result.exit_code == 0, result.output
    assert calls
    for call in calls:
        assert all(call.get(key) == value for key, value in expected.items())
    assert isinstance(json.loads(result.stdout), dict)


def test_conflicting_modes_fail_before_any_client_creation(monkeypatch):
    monkeypatch.setattr(cli, 'GitHubClient', lambda **kw: pytest.fail('must validate first'))
    result = runner.invoke(cli.app, ['--refresh', '--offline', 'inspect', URL, '--json'])
    assert result.exit_code == 2
    assert '--refresh' in result.output and '--offline' in result.output
    assert 'cannot' in result.output.lower()


def test_negative_cache_age_is_rejected():
    result = runner.invoke(cli.app, ['--cache-max-age', '-1', 'inspect', URL])
    assert result.exit_code == 2
    assert '0' in result.output and '--cache-max-age' in result.output


def test_options_do_not_leak_between_invocations(monkeypatch):
    calls = []
    def factory(**kwargs):
        calls.append(kwargs)
        return FakeClient()
    monkeypatch.setattr(cli, 'GitHubClient', factory)
    assert runner.invoke(cli.app, ['--offline', 'inspect', URL, '--json']).exit_code == 0
    assert runner.invoke(cli.app, ['inspect', URL, '--json']).exit_code == 0
    assert calls[0].get('offline') is True
    assert calls[1].get('offline', False) is False


@pytest.mark.parametrize('command', ['inspect', 'compare'])
def test_local_files_ignore_github_cache_policy(tmp_path, monkeypatch, command):
    path = tmp_path / 'SKILL.md'
    path.write_text(RAW, encoding='utf-8')
    monkeypatch.setattr(cli, 'GitHubClient', lambda **kw: pytest.fail('local input cannot initialize GitHub'))
    args = ['--offline', '--cache-max-age', '0', command, str(path)]
    if command == 'compare':
        args.append(str(path))
    result = runner.invoke(cli.app, [*args, '--json'])
    assert result.exit_code == 0, result.output


def test_real_offline_evidence_reads_timestamped_cache_without_auth_or_network(tmp_path, monkeypatch):
    monkeypatch.setenv('GITHUB_TOKEN', 'test-only-token')
    client = GitHubClient(tmp_path)
    client._http.close()
    def handler(request):
        if '/commits/' in request.url.path:
            return httpx.Response(200, json={'sha': COMMIT})
        if '/search/code' in request.url.path:
            return httpx.Response(200, json={'items': []})
        return httpx.Response(200, text=RAW)
    client._http = httpx.Client(transport=httpx.MockTransport(handler))
    snapshot = client.fetch_document(parse_github_url(URL))
    client.code_search('"name: source-demo" filename:SKILL.md')
    monkeypatch.setattr('skillvariants.github.resolve_token', lambda: pytest.fail('offline must not resolve auth'))
    monkeypatch.setattr(httpx.Client, 'get', lambda *a, **kw: pytest.fail('offline must not make network requests'))
    result = runner.invoke(cli.app, ['--offline', '--cache-max-age', '0', 'evidence', URL,
                                     '--cache-dir', str(tmp_path), '--json'])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload['target']['source']['raw_sha256'] == snapshot.source_metadata['raw_sha256']
    assert payload['target']['source']['resolved_ref'] == COMMIT
    assert payload['target']['source']['cache_status'] == 'offline'
    assert payload['target']['source']['stale'] is True
    assert payload['search']['cache']['cache_status'] == 'offline'
