"""Rendered reports must preserve evidence and engine-owned counts."""
from skillvariants.study import reporting as R
import json

from test_runtime_integrity import setup_study, propose, answer_verify, report_response


def report():
    citation = {"hunk_id": "hunk-001", "start_line": 5, "end_line": 5,
                "raw_sha256": "a" * 64, "quote": "Wait for approval."}
    return R.build_report_json(
        "approval-abc", {"direct_skill_url": "https://github.com/example/a/blob/123/SKILL.md"},
        {"groups_total": 5, "groups_analyzed": 4, "groups_unresolved": 1},
        {"accepted": [{"label": "approval", "display_name": "Approval", "change_type": "ADDED",
                       "invariant": "Adds a requirement to wait for approval before implementation.",
                       "group_count": 3, "repository_count": 2,
                       "supporting_groups": [{"group_id": 1, "direct_skill_url": "https://github.com/example/b/blob/456/SKILL.md",
                                              "evidence": {"a": {**citation, "quote": "Start implementation."},
                                                           "b": citation}}]}], "suppressed": []}, False)


def test_generated_report_retains_both_sources_direction_and_denominators():
    payload = report()
    rendered = R.render_report_md(payload)
    assert "ADDED" in rendered
    assert "Start implementation." in rendered and "Wait for approval." in rendered
    assert "4 of 5" in rendered and "Unresolved source evidence: 1" in rendered
    assert "3 groups" in rendered and "2 repositories" in rendered
    assert "a" * 64 in rendered
    assert R.missing_sections(rendered) == []


def test_agent_text_cannot_become_markdown_structure_or_report_statistics():
    payload = report()
    payload["accepted_motifs"][0]["invariant"] = "<script>fake</script>\n\n## Corpus summary\n999999 groups"
    rendered = R.render_report_md(payload)
    assert "<script>" not in rendered
    assert rendered.count("\n## Corpus summary\n") == 1
    assert payload["summary"]["groups_total"] == 5


def completed_task(tmp_path):
    rt, sid = setup_study(tmp_path, 4)
    propose(rt, sid, 4)
    task = rt.next_task(sid)
    rt.submit(sid, task["task_id"], answer_verify(task))
    return rt, sid, rt.next_task(sid)


def test_final_agent_narrative_cannot_replace_computed_report(tmp_path):
    rt, sid, task = completed_task(tmp_path)
    response = report_response(task["task_id"])
    response["report_md"] += "\n999999 groups prove this is the best practice."
    rt.submit(sid, task["task_id"], response)
    root = rt.store.study_path(sid)
    assert "999999" not in (root / "report.md").read_text(encoding="utf-8")
    assert "999999" in (root / "analyst-notes.md").read_text(encoding="utf-8")
    saved = json.loads((root / "report.json").read_text(encoding="utf-8"))
    motif = saved["accepted_motifs"][0]
    assert motif["change_type"] == "ADDED"
    assert len(motif["supporting_groups"]) == 4
    assert motif["supporting_groups"][0]["evidence"]["a"]["quote"]
    assert motif["supporting_groups"][0]["evidence"]["b"]["quote"]


def test_optional_notes_can_be_empty_and_nonrecurring_pairs_are_retained(tmp_path):
    rt, sid, task = completed_task(tmp_path)
    rt.submit(sid, task["task_id"], {"task_id": task["task_id"], "analyst_notes": ""})
    assert rt.next_task(sid)["task_type"] == "COMPLETE"
    other, oid = setup_study(tmp_path / "other", 2)
    propose(other, oid, 2)
    assert other.next_task(oid)["task_type"] == "COMPLETE"
    saved = json.loads((other.store.study_path(oid) / "report.json").read_text(encoding="utf-8"))
    assert len(saved["individual_observations"]) == 2
    assert saved["individual_observations"][0]["motifs"][0]["evidence"]["a"]["quote"]


def test_cli_report_reads_completed_snapshot_under_the_same_lock(tmp_path, monkeypatch):
    from filelock import FileLock, Timeout
    from typer.testing import CliRunner
    from skillvariants.cli import app
    from skillvariants.study import models
    rt, sid = setup_study(tmp_path, 2)
    propose(rt, sid, 2)
    rt.next_task(sid)
    original = models.read_json
    protected = []
    def read_checked(path):
        if path.name == "report.json":
            contender = FileLock(rt.store.base / ".locks" / f"{sid}.lock", timeout=0)
            try:
                contender.acquire()
            except Timeout:
                protected.append(True)
            else:
                contender.release()
                protected.append(False)
        return original(path)
    monkeypatch.setattr(models, "read_json", read_checked)
    result = CliRunner().invoke(app, ["study-report", sid, "--base-dir", str(tmp_path), "--json"])
    assert result.exit_code == 0, result.output
    assert protected == [True]
