"""Production evidence assembly, exercised with deterministic transport inputs."""
from __future__ import annotations

import json

from skillvariants.cli_helpers import build_evidence_payload
from skillvariants.github import CodeHit, GitHubError
from skillvariants.parser import GitHubRef, parse_skill_md

TARGET_URL = 'https://github.com/example/target/blob/main/skills/sample/SKILL.md'
BASE = ('---\nname: sample\ndescription: Diagnose software problems with evidence\n---\n'
        '# Debugging\nRead the failure and reproduce it before proposing any changes.\n'
        'Trace the cause, record evidence, and validate the smallest correction.\n'
        'Ask approval before deployment.\nReview tests and explain the result.\n')
VARIANT = BASE.replace('Ask approval', 'Request explicit approval')
OPPOSITE = BASE.replace('Ask approval', 'Do not ask approval')


class EvidenceClient:
    def __init__(self):
        self.files = {'target': BASE, 'variant': VARIANT, 'copy': VARIANT,
                      'opposite': OPPOSITE, 'exact': BASE,
                      'unrelated': '---\nname: sample\n---\nPomegranates bananas avocados cherries figs.'}

    def code_search(self, query, max_pages=3):
        return [CodeHit(f'example/{name}', 'skills/sample/SKILL.md', 'main', '', '')
                for name in [*self.files, 'unavailable']]

    def fetch_text(self, ref):
        if ref.repo not in self.files:
            raise GitHubError('Not found')
        return self.files[ref.repo]


def payload(monkeypatch):
    monkeypatch.setattr('skillvariants.cli_helpers.GitHubClient', lambda **kwargs: EvidenceClient())
    return build_evidence_payload(TARGET_URL)


def test_counts_use_explicit_denominators_after_relatedness_gate(monkeypatch):
    summary = payload(monkeypatch)['summary']
    assert summary['candidate_count'] == 6
    assert summary['related_variant_count'] == 3
    assert summary['fetched_count'] == 5
    assert summary['fetch_error_count'] == 1
    assert summary['unique_variant_count'] == 4
    assert summary['exact_copy_count'] == 1
    assert summary['mutation_group_count'] == 3


def test_opposite_rules_are_not_hidden_in_fuzzy_group(monkeypatch):
    groups = payload(monkeypatch)['groups']
    assert len(groups) == 3
    assert {g['repository'] for g in groups} == {'example/variant', 'example/opposite', 'example/exact'}
    assert all(g['member_count'] == 1 for g in groups)


def test_both_sources_line_evidence_hashes_and_occurrences_survive(monkeypatch):
    evidence = payload(monkeypatch)
    assert evidence['schema_version'] == '2'
    variant = next(g for g in evidence['groups'] if g['repository'] == 'example/variant')
    assert variant['occurrence_count'] == 2
    assert {o['repository'] for o in variant['occurrences']} == {'example/variant', 'example/copy'}
    comparison = variant['comparison']
    assert comparison['sources']['a']['raw_sha256']
    assert comparison['sources']['b']['raw_sha256']
    assert 'Ask approval before deployment.' in [line['text'] for h in comparison['hunks'] for line in h['a']['lines']]
    assert 'Request explicit approval before deployment.' in [line['text'] for h in comparison['hunks'] for line in h['b']['lines']]
    assert not evidence['target']['source']['immutable']
    assert 'absence' in comparison['evidence_policy']
    assert evidence['fetch_errors']
    json.dumps(evidence)


def test_excerpt_does_not_include_unified_diff_headers(monkeypatch):
    client = EvidenceClient()
    client.files = {'target': BASE, 'variant': VARIANT}
    monkeypatch.setattr('skillvariants.cli_helpers.GitHubClient', lambda **kwargs: client)
    for group in build_evidence_payload(TARGET_URL)['groups']:
        assert not group['added_excerpt'].startswith('++')
        assert not group['removed_excerpt'].startswith('--')


def test_production_builder_does_not_import_cli_state(monkeypatch):
    import builtins
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        assert name not in ('cli', 'skillvariants.cli'), 'evidence builder must not import CLI state'
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', guarded)
    payload(monkeypatch)


def test_production_builder_carries_authenticated_http_snapshots(tmp_path, monkeypatch):
    import httpx
    from pathlib import Path
    from skillvariants.github import GitHubClient
    monkeypatch.setenv('GITHUB_TOKEN', 'test-only-token')
    client = GitHubClient(tmp_path)
    client._http.close()
    def transport(request):
        assert request.headers['Authorization'] == 'Bearer test-only-token'
        if request.url.path == '/search/code':
            return httpx.Response(200, json={'items': [{
                'repository': {'full_name': 'example/variant'},
                'path': 'skills/sample/SKILL.md', 'sha': 'c' * 40,
            }]})
        if request.url.path == '/repos/example/variant':
            return httpx.Response(200, json={'default_branch': 'release/safe'})
        if '/commits/' in request.url.path:
            if request.url.path.endswith('/commits/main'):
                return httpx.Response(200, json={'sha': 'a' * 40})
            if request.url.path.endswith('/commits/release/safe'):
                return httpx.Response(200, json={'sha': 'b' * 40})
            return httpx.Response(404)
        assert '/contents/skills/sample/SKILL.md' in request.url.path
        if '/target/' in request.url.path:
            assert request.url.params['ref'] == 'a' * 40
            return httpx.Response(200, text=BASE)
        assert request.url.params['ref'] == 'b' * 40
        return httpx.Response(200, text=VARIANT)
    client._http = httpx.Client(transport=httpx.MockTransport(transport),
                                headers={'Authorization': 'Bearer test-only-token'})
    monkeypatch.setattr('skillvariants.cli_helpers.GitHubClient', lambda **kwargs: client)
    result = build_evidence_payload(TARGET_URL, cache_dir=tmp_path)
    assert result['target']['ref'] == 'a' * 40
    group = result['groups'][0]
    assert group['ref'] == 'b' * 40
    assert group['comparison']['sources']['b']['requested_ref'] == 'release/safe'
    assert Path(group['comparison']['sources']['a']['snapshot_path']).read_bytes() == BASE.encode()
    assert Path(group['comparison']['sources']['b']['snapshot_path']).read_bytes() == VARIANT.encode()
