"""Real process, crash, and snapshot regressions for persistent studies."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from skillvariants.study.runtime import StudyRuntime
from skillvariants.study.tasks import SubmissionError
from test_study_runtime import _fake_evidence, SYNTHETIC_BEFORE, SYNTHETIC_AFTER, URL
from test_runtime_integrity import answer_a, answer_verify, propose, report_response, setup_study


WORKER = r'''
import json, os, sys, time
from pathlib import Path
from skillvariants.study.runtime import StudyRuntime
config = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
rt = StudyRuntime(Path(config["base"]))
fault = config.get("fault")
if fault:
    original = getattr(rt.store, fault)
    def fail(*args, **kwargs):
        if fault == "save_manifest" and args[1].status != config.get("status"):
            return original(*args, **kwargs)
        if config.get("after_write", True):
            original(*args, **kwargs)
        os._exit(91)
    setattr(rt.store, fault, fail)
if config.get("hold"):
    original_save = rt.store.save_pass_a_batch
    def held(*args, **kwargs):
        Path(config["ready"]).write_text("ready")
        deadline = time.monotonic() + 15
        while not Path(config["release"]).exists():
            if time.monotonic() > deadline: raise RuntimeError("test barrier timed out")
            time.sleep(.02)
        return original_save(*args, **kwargs)
    rt.store.save_pass_a_batch = held
try:
    result = rt.submit(config["sid"], config["response"]["task_id"], config["response"],
                       force=config.get("force", False))
except (ValueError, OSError) as exc:
    result = {"error": str(exc), "type": type(exc).__name__}
Path(config["out"]).write_text(json.dumps(result), encoding="utf-8")
'''


def spawn_worker(tmp_path, name, rt, sid, response, **options):
    config = tmp_path / f"{name}.json"
    output = tmp_path / f"{name}-result.json"
    config.write_text(json.dumps({"base": str(rt.base_dir), "sid": sid, "response": response,
                                  "out": str(output), **options}), encoding="utf-8")
    proc = subprocess.Popen([sys.executable, "-B", "-c", WORKER, str(config)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc, output


def finish_worker(proc, expected=0):
    stdout, stderr = proc.communicate(timeout=20)
    assert proc.returncode == expected, stdout + stderr


@pytest.mark.parametrize("change", ["content", "occurrence", "membership"])
def test_changed_corpus_creates_new_study(tmp_path, change):
    evidence = _fake_evidence(2)
    rt = StudyRuntime(tmp_path, evidence_builder=lambda _: evidence)
    first = rt.start(URL)
    if change == "content":
        evidence["groups"][0]["comparison"]["sources"]["b"]["raw_sha256"] = "f" * 64
    elif change == "occurrence":
        evidence["groups"][0]["occurrences"] = [{"repository": "another/repository", "path": "SKILL.md",
                                                  "raw_sha256": "b" * 64}]
        evidence["groups"][0]["occurrence_count"] = 2
    else:
        evidence["groups"].pop()
    second = rt.start(URL)
    assert second["study_id"] != first["study_id"]
    assert not second["resumed"]


def test_corpus_identity_ignores_order_timestamps_and_cache_paths(tmp_path):
    evidence = _fake_evidence(2)
    rt = StudyRuntime(tmp_path, evidence_builder=lambda _: evidence)
    first = rt.start(URL)
    evidence["groups"].reverse()
    for group in evidence["groups"]:
        group["comparison"]["sources"]["b"].update(
            fetched_at="2099-01-01", cache_status="hit", snapshot_path="unavailable-cache.md", stale=True)
    resumed = rt.start(URL)
    assert resumed["resumed"] and resumed["study_id"] == first["study_id"]
    assert rt.store.load(first["study_id"]).manifest.get("corpus_fingerprint")


def test_study_owns_verified_full_source_snapshots_after_cache_clear(tmp_path):
    cache = tmp_path / "external-cache"
    cache.mkdir()
    evidence = _fake_evidence(2)
    for side, content in (("a", SYNTHETIC_BEFORE), ("b", SYNTHETIC_AFTER)):
        path = cache / f"{side}.md"
        path.write_bytes(content.encode("utf-8"))
        for group in evidence["groups"]:
            group["comparison"]["sources"][side]["snapshot_path"] = str(path)
    evidence["target"]["source"] = copy.deepcopy(evidence["groups"][0]["comparison"]["sources"]["a"])
    rt = StudyRuntime(tmp_path / "workspace", evidence_builder=lambda _: evidence)
    sid = rt.start(URL)["study_id"]
    for path in cache.iterdir():
        path.unlink()
    task = rt.next_task(sid)
    response = answer_a(task)
    for group in response["groups"]:
        for side in ("a", "b"):
            group["motifs"][0]["evidence"][side]["hunk_id"] = "full-source"
    assert rt.submit(sid, task["task_id"], response)["status"] == "ACCEPTED"
    for group in task["groups"]:
        for source in group["comparison"]["sources"].values():
            path = Path(source["snapshot_path"])
            assert path.is_relative_to(rt.store.study_path(sid) / "snapshots")
            assert hashlib.sha256(path.read_bytes()).hexdigest() == source["raw_sha256"]


def test_unverified_snapshot_path_is_not_advertised_as_full_source(tmp_path):
    evidence = _fake_evidence(2)
    bad = tmp_path / "mismatching.md"
    bad.write_text("not the claimed source", encoding="utf-8")
    evidence["groups"][0]["comparison"]["sources"]["a"]["snapshot_path"] = str(bad)
    rt = StudyRuntime(tmp_path / "workspace", evidence_builder=lambda _: evidence)
    sid = rt.start(URL)["study_id"]
    source = rt.next_task(sid)["groups"][0]["comparison"]["sources"]["a"]
    assert not source.get("snapshot_path")
    assert source["snapshot_available"] is False
    assert source["snapshot_error"]


@pytest.mark.parametrize("phase", ["pass_a", "pass_b", "final"])
def test_process_death_rolls_back_whole_transition_and_retry_completes(tmp_path, phase):
    rt, sid = setup_study(tmp_path / "workspace", 4)
    if phase == "pass_a":
        task = rt.next_task(sid)
        response = answer_a(task)
        fault = {"fault": "merge_pass_a"}
    elif phase == "pass_b":
        task = rt.next_task(sid)
        rt.submit(sid, task["task_id"], answer_a(task))
        task = rt.next_task(sid)
        response = {"task_id": task["task_id"], "canonical_motifs": []}
        fault = {"fault": "save_pass_b"}
    else:
        propose(rt, sid, 4)
        verifier = rt.next_task(sid)
        rt.submit(sid, verifier["task_id"], answer_verify(verifier))
        task = rt.next_task(sid)
        response = report_response(task["task_id"])
        fault = {"fault": "save_manifest", "status": "COMPLETE", "after_write": False}
    before = rt.store.load(sid)
    worker, _ = spawn_worker(tmp_path, phase, rt, sid, response, **fault)
    finish_worker(worker, 91)
    revived = StudyRuntime(rt.base_dir)
    recovered = revived.store.load(sid)
    assert recovered.manifest == before.manifest
    assert recovered.pass_a == before.pass_a
    assert recovered.pass_b == before.pass_b
    assert recovered.fingerprints == before.fingerprints
    assert revived.submit(sid, task["task_id"], response)["status"] == "ACCEPTED"
    if phase == "final":
        assert revived.status(sid)["status"] == "COMPLETE"
        assert revived.next_task(sid)["task_type"] == "COMPLETE"


def test_concurrent_conflicting_submissions_cannot_both_be_accepted(tmp_path):
    rt, sid = setup_study(tmp_path / "workspace", 4)
    task = rt.next_task(sid)
    first = answer_a(task)
    second = copy.deepcopy(first)
    second["groups"][0]["notes"] = "conflicting writer"
    ready, release = tmp_path / "ready", tmp_path / "release"
    worker_a, output_a = spawn_worker(tmp_path, "first", rt, sid, first,
        hold=True, ready=str(ready), release=str(release))
    try:
        deadline = time.monotonic() + 15
        while not ready.exists():
            if worker_a.poll() is not None or time.monotonic() > deadline:
                pytest.fail("first writer failed before reaching barrier")
            time.sleep(.02)
        worker_b, output_b = spawn_worker(tmp_path, "second", rt, sid, second)
        finish_worker(worker_b)
    finally:
        release.write_text("release")
        finish_worker(worker_a)
    results = [json.loads(path.read_text()) for path in (output_a, output_b)]
    assert sum(r.get("status") == "ACCEPTED" for r in results) == 1
    assert "busy" in results[1].get("error", "").lower()
    with pytest.raises(SubmissionError, match="conflicting"):
        rt.submit(sid, task["task_id"], second)
    assert rt.store.load(sid).pass_a["1"]["notes"] == first["groups"][0]["notes"]


def test_force_replacement_never_reuses_downstream_task_identity(tmp_path):
    rt, sid = setup_study(tmp_path, 4)
    first = rt.next_task(sid)
    original = answer_a(first)
    rt.submit(sid, first["task_id"], original)
    old_task = rt.next_task(sid)
    old_response = {"task_id": old_task["task_id"], "canonical_motifs": []}
    replacement = copy.deepcopy(original)
    replacement["groups"][0]["notes"] = "revised upstream evidence"
    rt.submit(sid, first["task_id"], replacement, force=True)
    new_task = rt.next_task(sid)
    assert new_task["task_id"] != old_task["task_id"]
    assert new_task["task_id"].startswith("pass-b-001")
    with pytest.raises(SubmissionError, match="dispatched|stale|generation"):
        rt.submit(sid, old_task["task_id"], old_response)


def test_complete_with_missing_report_is_not_announced_as_success(tmp_path):
    rt, sid = setup_study(tmp_path, 2)
    response = propose(rt, sid, 2)
    assert rt.next_task(sid)["task_type"] == "COMPLETE"
    (rt.store.study_path(sid) / "report.md").unlink()
    with pytest.raises((SubmissionError, OSError), match="report|artifact|incomplete"):
        rt.next_task(sid)
    with pytest.raises((SubmissionError, OSError), match="report|artifact|incomplete"):
        rt.submit(sid, response["task_id"], response)


def test_dispatched_payload_cannot_silently_change_before_submission(tmp_path):
    rt, sid = setup_study(tmp_path, 4)
    first = rt.next_task(sid)
    rt.submit(sid, first["task_id"], answer_a(first))
    task = rt.next_task(sid)
    path = rt.store.study_path(sid) / "pass-a-merged.json"
    groups = json.loads(path.read_text(encoding="utf-8"))
    groups["1"]["motifs"][0]["action"] = "Different proposed behavior"
    path.write_text(json.dumps(groups), encoding="utf-8")
    with pytest.raises(SubmissionError, match="payload|changed"):
        rt.submit(sid, task["task_id"], {"task_id": task["task_id"], "canonical_motifs": []})
    with pytest.raises(SubmissionError, match="payload|changed"):
        rt.next_task(sid)


def test_failed_initial_creation_never_publishes_partial_study(tmp_path, monkeypatch):
    import skillvariants.study.storage as storage
    original = storage.atomic_write_json
    def fail_on_evidence(path, data):
        if path.name == "evidence.json":
            raise OSError("injected disk write failure")
        return original(path, data)
    monkeypatch.setattr(storage, "atomic_write_json", fail_on_evidence)
    rt = StudyRuntime(tmp_path, evidence_builder=lambda _: _fake_evidence(2))
    with pytest.raises(OSError, match="injected"):
        rt.start(URL)
    assert list(rt.store.base.glob("*/manifest.json")) == []
    monkeypatch.setattr(storage, "atomic_write_json", original)
    sid = rt.start(URL)["study_id"]
    assert rt.next_task(sid)["task_type"] == "PASS_A_BATCH"


def test_escalated_groups_are_submitted_but_not_analyzed(tmp_path):
    rt, sid = setup_study(tmp_path, 6)
    task = rt.next_task(sid)
    response = answer_a(task)
    response["groups"][0].update(motifs=[], meaningful_behavior_change="PARTIAL",
                                  needs_source_escalation=True, reason="Full sources unavailable")
    rt.submit(sid, task["task_id"], response)
    counts = rt.status(sid)["counts"]
    assert counts["groups_submitted"] == 4
    assert counts["groups_analyzed"] == 3
    assert counts["groups_unresolved"] == 1
    assert counts["groups_pending"] == 2
