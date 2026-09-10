"""Verb-family heuristics must not discard real equivalent adaptations."""
import copy
import json

from skillvariants.comparison import compare_documents
from skillvariants.parser import parse_skill_md
from skillvariants.study.runtime import StudyRuntime
from test_study_runtime import _fake_evidence


def test_write_create_synonyms_reach_verification_and_three_group_recurrence(tmp_path):
    before = "---\nname: audit\n---\n# Deployment\nProceed with deployment.\n"
    after = ("---\nname: audit\n---\n# Deployment\n"
             "Create an audit report before deployment.\nProceed with deployment.\n")
    comparison = compare_documents(parse_skill_md(before), parse_skill_md(after))
    pair = {side: {"hunk_id": "hunk-001", "start_line": 5, "end_line": 5,
                   "quote": raw.splitlines()[4],
                   "raw_sha256": comparison["sources"][side]["raw_sha256"]}
            for side, raw in (("a", before), ("b", after))}
    evidence = _fake_evidence(1)
    for group in evidence["groups"]:
        group["comparison"] = comparison
    runtime = StudyRuntime(tmp_path, evidence_builder=lambda _: evidence)
    study_id = runtime.start("synthetic-audit")["study_id"]
    task = runtime.next_task(study_id)
    motif = {"action": "Write an audit report", "change_type": "ADDED",
             "invariant": "Requires an audit report to be created before deployment.",
             "behavior_signature": {"trigger": "before deployment", "action": "write an audit report",
                                    "object": "audit report", "outcome": "deployment is audited"},
             "evidence": pair, "confidence": .9}
    runtime.submit(study_id, task["task_id"], {
        "task_id": task["task_id"], "batch_id": task["batch_id"],
        "groups": [{"group_id": group["group_id"], "meaningful_behavior_change": "YES",
                    "motifs": [copy.deepcopy(motif)], "needs_source_escalation": False}
                   for group in task["groups"]]})
    task = runtime.next_task(study_id)
    runtime.submit(study_id, task["task_id"], {
        "task_id": task["task_id"], "canonical_motifs": [{
            "label": "audit-report", "invariant": motif["invariant"], "change_type": "ADDED",
            "behavior_signature": {**motif["behavior_signature"], "action": "create an audit report"},
            "supporting_groups": [1, 2, 3]}]})
    task = runtime.next_task(study_id)
    assert task["task_type"] == "VERIFY_MOTIF"
    assert len(task["groups"]) == 3
    for group in task["groups"]:
        assert "does not prove" in group["verification_concern"]
        assert "write an audit report" in group["verification_concern"]
        assert "create an audit report" in group["verification_concern"]
    assert runtime.next_task(study_id) == task
    runtime.submit(study_id, task["task_id"], {
        "task_id": task["task_id"], "motif_label": "audit-report",
        "decisions": [{"group_id": group["group_id"], "decision": "YES", "confidence": .9,
                       "reason": "Writing and creating the same report express the cited requirement.",
                       "evidence": pair} for group in task["groups"]]})
    task = runtime.next_task(study_id)
    assert task["task_type"] == "FINAL_REPORT"
    runtime.submit(study_id, task["task_id"], {"task_id": task["task_id"], "analyst_notes": ""})
    report = json.loads((runtime.store.study_path(study_id) / "report.json").read_text())
    accepted = report["accepted_motifs"][0]
    assert accepted["group_count"] == accepted["repository_count"] == 3
    assert len(accepted["supporting_groups"]) == 3
    assert report["suppressed_motifs"] == []
