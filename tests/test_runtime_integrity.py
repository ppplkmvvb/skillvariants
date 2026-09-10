"""Regression coverage for persisted task membership and safe finalization."""
import copy
import json

import pytest

from skillvariants.study.runtime import StudyRuntime
from skillvariants.study.tasks import SubmissionError
from test_study_runtime import _fake_evidence, GOOD_GROUP_RESPONSE, URL


def setup_study(tmp_path, count=10, batch_size=4):
    evidence = _fake_evidence(count - 2)
    rt = StudyRuntime(tmp_path, evidence_builder=lambda _: evidence, batch_size=batch_size)
    return rt, rt.start(URL)["study_id"]


def answer_a(task):
    return {"task_id": task["task_id"], "batch_id": task["batch_id"],
            "groups": [{**copy.deepcopy(GOOD_GROUP_RESPONSE), "group_id": g["group_id"]}
                       for g in task["groups"]]}


def propose(rt, sid, count, label="stop"):
    while (task := rt.next_task(sid))["task_type"] == "PASS_A_BATCH":
        rt.submit(sid, task["task_id"], answer_a(task))
    motif = GOOD_GROUP_RESPONSE["motifs"][0]
    response = {"task_id": task["task_id"], "canonical_motifs": [{
        "label": label, "invariant": motif["invariant"], "change_type": motif["change_type"],
        "behavior_signature": motif["behavior_signature"],
        "supporting_groups": list(range(1, count + 1))}]}
    rt.submit(sid, task["task_id"], response)
    return response


def answer_verify(task, no_ids=()):
    return {"task_id": task["task_id"], "motif_label": task["motif_label"],
            "decisions": [{"group_id": g["group_id"],
                           "decision": "NO" if g["group_id"] in no_ids else "YES",
                           "reason": "paired source inspected", "confidence": .9,
                           "evidence": GOOD_GROUP_RESPONSE["motifs"][0]["evidence"]}
                          for g in task["groups"]]}


def report_response(task_id):
    return {"task_id": task_id, "report_md": "\n".join(
        "## " + s for s in ["Target Skill", "Corpus summary", "Recurring adaptations",
                             "Notable one-offs", "Caveats"])}


def test_partial_pass_a_cannot_mark_batch_complete(tmp_path):
    rt, sid = setup_study(tmp_path, 8, 8)
    task = rt.next_task(sid)
    response = answer_a(task)
    response["groups"] = response["groups"][:1]
    with pytest.raises(SubmissionError, match="missing.*groups"):
        rt.submit(sid, task["task_id"], response)
    assert rt.status(sid)["counts"]["groups_analyzed"] == 0


def test_resume_preserves_partition_after_batch_size_change(tmp_path):
    rt, sid = setup_study(tmp_path, 10, 4)
    task = rt.next_task(sid)
    rt.submit(sid, task["task_id"], answer_a(task))
    revived = StudyRuntime(tmp_path, batch_size=8)
    task = revived.next_task(sid)
    assert [g["group_id"] for g in task["groups"]] == [5, 6, 7, 8]
    rt.submit(sid, task["task_id"], answer_a(task))
    assert [g["group_id"] for g in revived.next_task(sid)["groups"]] == [9, 10]


def test_source_identity_distinguishes_same_name_and_hash(tmp_path):
    first = _fake_evidence()
    other = copy.deepcopy(first)
    other["target"]["repository"] = "other/repo"
    rt = StudyRuntime(tmp_path, evidence_builder=lambda url: first if url == "first" else other)
    a = rt.start("first")
    b = rt.start("other")
    assert a["study_id"] != b["study_id"]
    assert not b["resumed"]


def test_verifies_all_original_members_with_original_denominator(tmp_path):
    rt, sid = setup_study(tmp_path, 10)
    propose(rt, sid, 10)
    seen = []
    while (task := rt.next_task(sid))["task_type"] == "VERIFY_MOTIF":
        assert len(task["groups"]) <= 8
        seen.extend(g["group_id"] for g in task["groups"])
        rt.submit(sid, task["task_id"], answer_verify(task, no_ids=(9, 10)))
    assert seen == list(range(1, 11))
    assert task["task_type"] == "FINAL_REPORT"
    motif = task["accepted_motifs"][0]
    assert motif["rejection_rate"] == .2
    assert motif["proposed_group_count"] == 10
    assert motif["group_count"] == 8


def test_oversized_cluster_is_explicitly_suppressed(tmp_path):
    rt, sid = setup_study(tmp_path, 20)
    propose(rt, sid, 20)
    task = rt.next_task(sid)
    assert task["task_type"] == "COMPLETE"
    report = json.loads((rt.store.base / sid / "report.json").read_text())
    suppressed = report["suppressed_motifs"][0]
    assert suppressed["status"] == "SPLIT_REQUIRED"
    assert suppressed["proposed_group_count"] == 20
    assert suppressed["reasons"]


def test_no_motif_completion_has_both_reports(tmp_path):
    rt, sid = setup_study(tmp_path, 2)
    propose(rt, sid, 2)
    assert rt.next_task(sid)["task_type"] == "COMPLETE"
    root = rt.store.base / sid
    assert (root / "report.md").is_file()
    report = json.loads((root / "report.json").read_text())
    assert report["accepted_motifs"] == []
    assert report["summary"]["groups_analyzed"] == 2


def test_early_report_cannot_create_report_or_advance(tmp_path):
    rt, sid = setup_study(tmp_path)
    with pytest.raises(SubmissionError, match="dispatched|completion|pending"):
        rt.submit(sid, "final-report-999", report_response("final-report-999"))
    assert not (rt.store.base / sid / "report.md").exists()


def test_outer_verifier_id_must_bind_to_dispatched_task(tmp_path):
    rt, sid = setup_study(tmp_path, 4)
    propose(rt, sid, 4)
    task = rt.next_task(sid)
    with pytest.raises(SubmissionError, match="task_id|dispatched"):
        rt.submit(sid, "verify-arbitrary", answer_verify(task))


def test_verifier_cannot_submit_before_dispatch(tmp_path):
    rt, sid = setup_study(tmp_path, 4)
    propose(rt, sid, 4)
    response = {"task_id": "verify-001", "motif_label": "stop", "decisions": [
        {"group_id": gid, "decision": "YES", "confidence": .9} for gid in range(1, 5)]}
    with pytest.raises(SubmissionError, match="dispatched"):
        rt.submit(sid, "verify-001", response)


def test_force_pass_a_invalidates_all_downstream_artifacts(tmp_path):
    rt, sid = setup_study(tmp_path, 4)
    task = rt.next_task(sid)
    original = answer_a(task)
    rt.submit(sid, task["task_id"], original)
    propose(rt, sid, 4)
    verifier = rt.next_task(sid)
    rt.submit(sid, verifier["task_id"], answer_verify(verifier))
    final = rt.next_task(sid)
    rt.submit(sid, final["task_id"], report_response(final["task_id"]))
    replacement = copy.deepcopy(original)
    replacement["groups"][0]["notes"] = "corrected"
    rt.submit(sid, task["task_id"], replacement, force=True)
    state = rt.store.load(sid)
    assert state.pass_b is None
    assert state.verification == {}
    assert set(state.fingerprints) == {task["task_id"]}
    for filename in ("pass-b-proposed.json", "motifs.json", "report.json", "report.md"):
        assert not (rt.store.base / sid / filename).exists()
    assert rt.next_task(sid)["task_type"] == "PASS_B_CONSOLIDATE"


@pytest.mark.parametrize("sid", ["../outside", "..\\outside", "C:\\outside", "a/b", "", "."])
def test_rejects_unsafe_study_ids(tmp_path, sid):
    rt = StudyRuntime(tmp_path)
    with pytest.raises(ValueError, match="study.id"):
        rt.status(sid)


def test_missing_study_has_actionable_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="study.*study-start"):
        StudyRuntime(tmp_path).status("missing-study")


def test_force_pass_b_invalidates_verification_and_report(tmp_path):
    rt, sid = setup_study(tmp_path, 4)
    original = propose(rt, sid, 4)
    task = rt.next_task(sid)
    rt.submit(sid, task["task_id"], answer_verify(task))
    final = rt.next_task(sid)
    rt.submit(sid, final["task_id"], report_response(final["task_id"]))
    replacement = copy.deepcopy(original)
    replacement["canonical_motifs"][0]["label"] = "revised-stop"
    rt.submit(sid, original["task_id"], replacement, force=True)
    state = rt.store.load(sid)
    assert state.verification == {}
    assert not any(k.startswith(("verify-", "final-report-")) for k in state.fingerprints)
    assert not (rt.store.base / sid / "report.json").exists()
    assert rt.next_task(sid)["motif_label"] == "revised-stop"


def test_force_verifier_replaces_chunk_and_invalidates_final_report(tmp_path):
    rt, sid = setup_study(tmp_path, 10)
    propose(rt, sid, 10)
    first = rt.next_task(sid)
    rt.submit(sid, first["task_id"], answer_verify(first))
    second = rt.next_task(sid)
    rt.submit(sid, second["task_id"], answer_verify(second))
    final = rt.next_task(sid)
    rt.submit(sid, final["task_id"], report_response(final["task_id"]))
    rt.submit(sid, second["task_id"], answer_verify(second, (9, 10)), force=True)
    state = rt.store.load(sid)
    assert len(state.verification["stop"]) == 10
    assert final["task_id"] not in state.fingerprints
    assert not (rt.store.base / sid / "report.md").exists()
    assert rt.next_task(sid)["accepted_motifs"][0]["rejection_rate"] == .2


def test_duplicate_canonical_labels_rejected(tmp_path):
    rt, sid = setup_study(tmp_path, 4)
    original = propose(rt, sid, 4)
    duplicate = copy.deepcopy(original)
    duplicate["canonical_motifs"] *= 2
    with pytest.raises(SubmissionError, match="duplicate.*label"):
        rt.submit(sid, original["task_id"], duplicate, force=True)


def test_empty_cluster_rejected(tmp_path):
    rt, sid = setup_study(tmp_path, 4)
    original = propose(rt, sid, 4)
    empty = copy.deepcopy(original)
    empty["canonical_motifs"][0]["supporting_groups"] = []
    with pytest.raises(SubmissionError, match="non-empty"):
        rt.submit(sid, original["task_id"], empty, force=True)


def test_duplicate_canonical_members_rejected(tmp_path):
    rt, sid = setup_study(tmp_path, 4)
    original = propose(rt, sid, 4)
    duplicate = copy.deepcopy(original)
    duplicate["canonical_motifs"][0]["supporting_groups"] = [1, 1, 2]
    with pytest.raises(SubmissionError, match="duplicate.*group"):
        rt.submit(sid, original["task_id"], duplicate, force=True)


def test_legacy_protocol_cannot_silently_resume(tmp_path):
    rt, sid = setup_study(tmp_path, 4)
    from skillvariants.study.models import atomic_write_json
    state = rt.store.load(sid)
    state.manifest["runtime_version"] = "0.2"
    atomic_write_json(rt.store.study_path(sid) / "manifest.json", state.manifest)
    with pytest.raises(SubmissionError, match="legacy.*study-start"):
        rt.next_task(sid)


def test_empty_corpus_completes_with_readable_reports(tmp_path):
    evidence = _fake_evidence()
    evidence["groups"] = []
    rt = StudyRuntime(tmp_path, evidence_builder=lambda _: evidence)
    sid = rt.start(URL)["study_id"]
    task = rt.next_task(sid)
    rt.submit(sid, task["task_id"], {"task_id": task["task_id"], "canonical_motifs": []})
    assert rt.next_task(sid)["task_type"] == "COMPLETE"
    assert (rt.store.study_path(sid) / "report.md").is_file()


@pytest.mark.parametrize("group", [None, [], "bad group"])
def test_malformed_group_is_actionable_and_does_not_advance(tmp_path, group):
    rt, sid = setup_study(tmp_path, 4)
    task = rt.next_task(sid)
    response = answer_a(task)
    response["groups"][0] = group
    with pytest.raises(SubmissionError, match="object"):
        rt.submit(sid, task["task_id"], response)
    assert rt.status(sid)["counts"]["groups_analyzed"] == 0


def test_storage_writes_reject_unsafe_study_id(tmp_path):
    rt = StudyRuntime(tmp_path)
    with pytest.raises(ValueError, match="study.id"):
        rt.store.save_report_md("../outside", "must not write")
