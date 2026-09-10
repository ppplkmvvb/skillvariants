"""Public command regressions, exercising Typer rather than calling handlers."""
from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
from rich.text import Text
from typer.testing import CliRunner

from skillvariants import cli
from skillvariants.github import AuthError
from skillvariants.study.storage import StudyStore

runner = CliRunner()
URL = "https://github.com/example/skills/blob/main/SKILL.md"
TEXT = "---\nname: 示例 🚀\nupdated: 2026-09-10\n---\nAsk for approval before editing.\n"


def create_study(base: Path):
    store = StudyStore(base)
    target = {"repository": "example/skills", "path": "SKILL.md", "ref": "main",
              "direct_skill_url": URL, "name": "demo", "normalized_hash": "a" * 64}
    sid, state = store.create(target, "a" * 64, {"target": target, "groups": []}, [], False)
    return store, sid, state


@pytest.mark.parametrize("command", ["evidence", "study-start", "study-status", "study-next", "study-submit", "study-report"])
def test_json_is_a_documented_flag(command):
    result = runner.invoke(cli.app, [command, "--help"], color=False)
    assert result.exit_code == 0
    assert "--json" in Text.from_ansi(result.stdout).plain


def test_default_study_base_is_current_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _, sid, _ = create_study(tmp_path)
    result = runner.invoke(cli.app, ["study-status", sid])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["study_id"] == sid
    assert not (tmp_path / ".skillvariants" / ".skillvariants").exists()


def test_report_reads_persisted_report_from_custom_workspace(tmp_path):
    store, sid, state = create_study(tmp_path)
    state.manifest["status"] = "COMPLETE"
    store.save_manifest(sid, state)
    report = {"study_id": sid, "motifs": [], "marker": "persisted report"}
    store.save_report_json(sid, report)
    store.save_report_md(sid, "# Generated report")
    store.save_motifs(sid, {"accepted": [], "suppressed": []})
    result = runner.invoke(cli.app, ["study-report", sid, "--base-dir", str(tmp_path), "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == report


@pytest.mark.parametrize("command", ["study-status", "study-next", "study-report"])
def test_missing_study_is_actionable_error_without_traceback(command, tmp_path):
    result = runner.invoke(cli.app, [command, "missing", "--base-dir", str(tmp_path)])
    assert result.exit_code != 0
    assert isinstance(result.exception, SystemExit), repr(result.exception)
    assert result.stdout == ""
    assert "Error:" in result.stderr
    assert "missing" in result.stderr


def test_authentication_failure_is_actionable(monkeypatch):
    def denied(**kwargs):
        raise AuthError("Set GITHUB_TOKEN or run gh auth login")
    monkeypatch.setattr(cli, "GitHubClient", denied)
    result = runner.invoke(cli.app, ["inspect", URL, "--json"])
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit), repr(result.exception)
    assert "GITHUB_TOKEN" in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("contents", ["[", "[]", "null"])
def test_submit_rejects_invalid_json_document_cleanly(tmp_path, contents):
    response = tmp_path / "response.json"
    response.write_text(contents, encoding="utf-8")
    result = runner.invoke(cli.app, ["study-submit", "missing", str(response), "--base-dir", str(tmp_path)])
    assert result.exit_code != 0
    assert isinstance(result.exception, SystemExit), repr(result.exception)
    assert "Error:" in result.stderr


def test_local_inspect_preserves_yaml_dates_and_source_without_auth(tmp_path, monkeypatch):
    path = tmp_path / "SKILL.md"
    path.write_text(TEXT, encoding="utf-8")
    def forbidden(**kwargs):
        pytest.fail("Local files must not initialize a GitHub client")
    monkeypatch.setattr(cli, "GitHubClient", forbidden)
    result = runner.invoke(cli.app, ["inspect", str(path), "--json"])
    assert result.exit_code == 0, repr(result.exception)
    payload = json.loads(result.stdout)
    assert payload["name"] == "示例 🚀"
    assert payload["frontmatter"]["updated"] == "2026-09-10"
    assert payload["ref"] == {"kind": "local", "path": str(path.resolve())}


def test_local_compare_has_paired_diff_and_original_contract(tmp_path, monkeypatch):
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text(TEXT, encoding="utf-8")
    b.write_text(TEXT.replace("Ask for approval", "Do not ask for approval"), encoding="utf-8")
    monkeypatch.setattr(cli, "GitHubClient", lambda **kw: pytest.fail("unexpected auth"))
    result = runner.invoke(cli.app, ["compare", str(a), str(b), "--json"])
    assert result.exit_code == 0, repr(result.exception)
    payload = json.loads(result.stdout)
    assert payload["a"] == str(a.resolve()) and payload["b"] == str(b.resolve())
    assert "similarity" in payload and "classification" in payload
    comparison = payload["comparison"]
    assert "-Ask for approval" in comparison["unified_diff"]
    assert "+Do not ask for approval" in comparison["unified_diff"]
    assert comparison["hunks"]
    assert comparison["sources"]["a"]["kind"] == "local"
    assert comparison["sources"]["a"]["path"] == str(a.resolve())


def test_module_entrypoint_json_survives_gbk_stdout(tmp_path):
    path = tmp_path / "SKILL.md"
    path.write_text(TEXT, encoding="utf-8")
    env = {**os.environ, "PYTHONIOENCODING": "gbk:strict", "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, "-B", "-m", "skillvariants.cli", "inspect", str(path), "--json"],
                            env=env, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode("gbk", errors="replace")
    assert json.loads(result.stdout.decode("gbk"))["name"] == "示例 🚀"


def test_inspect_remote_yaml_date_is_json_serializable(monkeypatch):
    class Client:
        def fetch_text(self, ref):
            return TEXT
    monkeypatch.setattr(cli, "GitHubClient", lambda **kwargs: Client())
    result = runner.invoke(cli.app, ["inspect", URL, "--json"])
    assert result.exit_code == 0, repr(result.exception)
    assert json.loads(result.stdout)["frontmatter"]["updated"] == "2026-09-10"


@pytest.mark.parametrize("command", ["inspect", "compare"])
def test_missing_local_file_is_clean_error(command, tmp_path):
    missing = str(tmp_path / "missing.md")
    args = [command, missing] + ([missing] if command == "compare" else [])
    result = runner.invoke(cli.app, [*args, "--json"])
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert "missing.md" in result.stderr
    assert result.stdout == ""


def test_incomplete_study_cannot_emit_a_report(tmp_path):
    store, sid, _ = create_study(tmp_path)
    store.save_report_json(sid, {"stale": True})
    result = runner.invoke(cli.app, ["study-report", sid, "--base-dir", str(tmp_path), "--json"])
    assert result.exit_code != 0
    assert "not complete" in result.stderr
    assert result.stdout == ""


def test_study_status_and_next_accept_json_at_real_entrypoint(tmp_path):
    _, sid, _ = create_study(tmp_path)
    for command in ("study-status", "study-next"):
        result = runner.invoke(cli.app, [command, sid, "--base-dir", str(tmp_path), "--json"])
        assert result.exit_code == 0, repr(result.exception)
        assert isinstance(json.loads(result.stdout), dict)


def test_related_counts_use_gate_and_explicit_fetch_denominators(tmp_path, monkeypatch):
    from conftest import FakeGitHubClient
    from skillvariants.github import CodeHit
    from tests_helpers import TARGET_BODY, TARGET_URL, doc_text

    files = {
        ("test/target", "skills/sample/SKILL.md", "main"): doc_text(TARGET_BODY),
        ("copy/repo", "SKILL.md", "main"): doc_text(TARGET_BODY),
        ("other/repo", "SKILL.md", "main"): "---\nname: unrelated\n---\n紫色苹果星际旅行\n",
    }
    hits = [CodeHit(repo=r, path="SKILL.md", default_branch="main", sha="", api_url="")
            for r in ("copy/repo", "other/repo", "missing/repo")]
    client = FakeGitHubClient(files, hits)
    monkeypatch.setattr(cli, "GitHubClient", lambda **kwargs: client)
    result = runner.invoke(cli.app, ["related", TARGET_URL, "--cache-dir", str(tmp_path), "--json"])
    assert result.exit_code == 0, repr(result.exception)
    payload = json.loads(result.stdout)
    assert payload["unique_related_variants"] == 1
    assert payload["counts"]["candidates_total"] == 3
    assert payload["counts"]["candidates_fetched"] == 2
    assert payload["counts"]["candidates_failed"] == 1
    assert payload["counts"]["unique_variants"] == 2
    assert payload["counts"]["related_unique_variants"] == 1
    assert payload["counts"]["unrelated_unique_variants"] == 1


def test_local_source_hash_preserves_windows_newlines(tmp_path):
    path = tmp_path / "SKILL.md"
    raw = TEXT.replace("\n", "\r\n").encode("utf-8")
    path.write_bytes(raw)
    result = runner.invoke(cli.app, ["inspect", str(path), "--json"])
    assert result.exit_code == 0, repr(result.exception)
    assert json.loads(result.stdout)["source"]["raw_sha256"] == hashlib.sha256(raw).hexdigest()


def test_evidence_accepts_json_at_real_entrypoint(monkeypatch):
    from skillvariants import cli_helpers
    monkeypatch.setattr(cli_helpers, "build_evidence_payload", lambda *args, **kwargs: {"schema_version": "1", "groups": []})
    result = runner.invoke(cli.app, ["evidence", URL, "--json"])
    assert result.exit_code == 0, repr(result.exception)
    assert json.loads(result.stdout)["groups"] == []


def test_study_start_creates_session_at_workspace_root(tmp_path, monkeypatch):
    from skillvariants import cli_helpers
    monkeypatch.chdir(tmp_path)
    target = {"repository": "example/skills", "path": "SKILL.md", "ref": "main",
              "direct_skill_url": URL, "name": "demo", "normalized_hash": "b" * 64}
    monkeypatch.setattr(cli_helpers, "build_evidence_payload", lambda *args, **kwargs: {"target": target, "groups": []})
    result = runner.invoke(cli.app, ["study-start", URL, "--json"])
    assert result.exit_code == 0, repr(result.exception)
    sid = json.loads(result.stdout)["study_id"]
    assert (tmp_path / ".skillvariants" / "studies" / sid / "manifest.json").is_file()
    assert not (tmp_path / ".skillvariants" / ".skillvariants").exists()
