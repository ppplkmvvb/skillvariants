"""Study runtime tests: state machine, batching, idempotency, malformed
submissions, resume, sampling, and source-URL preservation (spec 21/23/25)."""
from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from skillvariants.cli import app
from skillvariants.study.models import (
    MAX_SEMANTIC_GROUPS,
    atomic_write_json,
)
from skillvariants.study.runtime import StudyRuntime
from skillvariants.study import tasks as T

from conftest import (
    LOOPKIT_SD,
    SUPERPOWERS_SD,
    VIBESKILLS_SD,
    fixture_text,
)
from skillvariants.github import CodeHit


def _fake_evidence(n_extra_groups: int = 6) -> dict:
    """Small deterministic evidence payload: 2 real fixture groups + N synthetic."""
    base = {
        "schema_version": "1",
        "target": {
            "repository": "obra/superpowers",
            "path": "skills/systematic-debugging/SKILL.md",
            "ref": "main",
            "direct_skill_url": "https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md",
            "name": "systematic-debugging",
            "normalized_hash": "a" * 64,
        },
        "summary": {"candidate_count": 3, "related_variant_count": 2 + n_extra_groups,
                    "exact_copy_count": 0, "mutation_group_count": 2 + n_extra_groups,
                    "broad_archetype_counts": {"compact-rewrite": 1,
                                               "routing-specialization": 1}},
        "groups": [],
    }
    real = [
        {"group_id": 1, "repository": "Archive228/loopkit",
         "path": "skills/systematic-debugging/SKILL.md", "ref": "main",
         "direct_skill_url": "https://github.com/Archive228/loopkit/blob/main/skills/systematic-debugging/SKILL.md",
         "archetype": "compact-rewrite", "relatedness": 0.54,
         "member_count": 1, "occurrence_count": 1,
         "structural_signals": {"length_delta": -0.85, "headings_added": 3,
                                "headings_removed": 14, "commands_added": [],
                                "commands_removed": ["bash"],
                                "cross_skill_ref_delta": 0, "routing_signals": [],
                                "wrapper_signals": [], "workflow_structure_delta": 0.9,
                                "placeholder_signal": 0.0},
         "added_excerpt": "The loop 1. Read the whole error",
         "removed_excerpt": "## Overview"},
        {"group_id": 2, "repository": "foryourhealth111-pixel/Vibe-Skills",
         "path": "bundled/skills/systematic-debugging/SKILL.md", "ref": "main",
         "direct_skill_url": "https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/bundled/skills/systematic-debugging/SKILL.md",
         "archetype": "routing-specialization", "relatedness": 0.86,
         "member_count": 1, "occurrence_count": 1,
         "structural_signals": {"length_delta": 1.1, "headings_added": 2,
                                "headings_removed": 0, "commands_added": [],
                                "commands_removed": [], "cross_skill_ref_delta": 3,
                                "routing_signals": ["routing boundary"], "wrapper_signals": [],
                                "workflow_structure_delta": 0.1, "placeholder_signal": 0.0},
         "added_excerpt": "## Routing Boundary Do not use for test-first work",
         "removed_excerpt": ""},
    ]
    synthetic = []
    for i in range(n_extra_groups):
        gid = 3 + i
        synthetic.append({
            "group_id": gid, "repository": f"repo{i}/clone",
            "path": f"s{i}/SKILL.md", "ref": "main",
            "direct_skill_url": f"https://github.com/repo{i}/clone/blob/main/s{i}/SKILL.md",
            "archetype": "compact-rewrite", "relatedness": 0.4,
            "member_count": 1, "occurrence_count": 1,
            "structural_signals": {"length_delta": -0.5, "headings_added": 2,
                                   "headings_removed": 3, "commands_added": [],
                                   "commands_removed": [], "cross_skill_ref_delta": 0,
                                   "routing_signals": [], "wrapper_signals": [],
                                   "workflow_structure_delta": 0.2,
                                   "placeholder_signal": 0.0},
            "added_excerpt": f"compact loop variant {i}",
            "removed_excerpt": "## Overview",
        })
    base["groups"] = real + synthetic
    return base


@pytest.fixture
def runtime(tmp_path):
    return StudyRuntime(
        base_dir=tmp_path,
        evidence_builder=lambda url: _fake_evidence(),
        batch_size=4,
    )


URL = ("https://github.com/obra/superpowers/blob/main/"
       "skills/systematic-debugging/SKILL.md")

GOOD_GROUP_RESPONSE = {
    "group_id": 1,
    "meaningful_behavior_change": "YES",
    "motifs": [{
        "action": "Add stop conditions after failed attempts",
        "invariant": "Introduces a stop condition triggered by repeated failed fix attempts.",
        "behavior_signature": {"trigger": "repeated failed fixes", "action": "stop or escalate",
                               "object": "debugging loop", "outcome": "bounded loop"},
        "evidence_summary": "loop + stop conditions added",
        "confidence": 0.9,
    }],
    "needs_source_escalation": False,
    "notes": "",
}

ROUTING_RESPONSE = {
    "group_id": 2,
    "meaningful_behavior_change": "YES",
    "motifs": [{
        "action": "Add routing boundary for test-first work",
        "invariant": "Adds a boundary declaring when the skill must not be used.",
        "behavior_signature": {"trigger": "test-first request", "action": "decline",
                               "object": "skill activation", "outcome": "handoff"},
        "evidence_summary": "routing boundary section",
        "confidence": 0.9,
    }],
    "needs_source_escalation": False,
    "notes": "",
}


def _pass_a_response_for(runtime, study_id: str, overrides: dict | None = None) -> dict:
    task = runtime.next_task(study_id)
    # deep-copy templates: later tests mutate nested fields in-place
    import copy
    assert task["task_type"] == "PASS_A_BATCH"
    groups = []
    for g in task["groups"]:
        if overrides and g["group_id"] in overrides:
            groups.append(overrides[g["group_id"]])
            continue
        if g["group_id"] == 1:
            groups.append({**copy.deepcopy(GOOD_GROUP_RESPONSE), "group_id": g["group_id"]})
        elif g["group_id"] == 2:
            groups.append({**copy.deepcopy(ROUTING_RESPONSE), "group_id": g["group_id"]})
        else:
            groups.append({
                "group_id": g["group_id"], "meaningful_behavior_change": "NO",
                "motifs": [], "needs_source_escalation": False, "notes": "",
            })
    return {"task_id": task["task_id"], "batch_id": task["batch_id"], "groups": groups}


class TestStudyLifecycle:
    def test_start_creates_evidence_ready(self, runtime) -> None:
        result = runtime.start(URL)
        assert result["resumed"] is False
        assert result["status"] == "EVIDENCE_READY"
        state = runtime.store.load(result["study_id"])
        assert state.manifest["counts"]["groups_total"] == 8

    def test_resume_returns_existing_study(self, runtime) -> None:
        first = runtime.start(URL)
        second = runtime.start(URL)
        assert second["study_id"] == first["study_id"]
        assert second["resumed"] is True

    def test_full_loop_reaches_complete(self, runtime) -> None:
        start = runtime.start(URL)
        sid = start["study_id"]
        # pass A: 2 batches of 4
        for _ in range(2):
            response = _pass_a_response_for(runtime, sid)
            result = runtime.submit(sid, response["task_id"], response)
            assert result["status"] == "ACCEPTED"
        task = runtime.next_task(sid)
        assert task["task_type"] == "PASS_B_CONSOLIDATE"
        pass_b = {
            "task_id": task["task_id"],
            "canonical_motifs": [
                {"label": "add-stop-conditions", "display_name": "Add stop conditions",
                 "invariant": "Introduces a stop condition triggered by repeated failed fix attempts.",
                 "behavior_signature": GOOD_GROUP_RESPONSE["motifs"][0]["behavior_signature"],
                 "supporting_groups": [1], "rejected_near_misses": []},
                {"label": "add-routing-boundary", "display_name": "Add routing boundary",
                 "invariant": "Adds a boundary declaring when the skill must not be used.",
                 "behavior_signature": ROUTING_RESPONSE["motifs"][0]["behavior_signature"],
                 "supporting_groups": [2], "rejected_near_misses": []},
            ],
        }
        result = runtime.submit(sid, pass_b["task_id"], pass_b)
        assert result["status"] == "ACCEPTED"
        # verify each motif (only >=3-group motifs get verify tasks; these have
        # 1 group each so the runtime goes straight to finalize)
        task = runtime.next_task(sid)
        # with <3 supporting groups both motifs are non-recurring -> COMPLETE
        assert task["task_type"] == "COMPLETE"

    def test_complete_flow_with_recurrence_and_report(self, runtime) -> None:
        start = runtime.start(URL)
        sid = start["study_id"]
        # fill 4 groups with the same stop-condition motif + 1 routing = recurring
        def response_for(task):
            groups = []
            for g in task["groups"]:
                if g["group_id"] == 2:
                    groups.append(dict(ROUTING_RESPONSE, group_id=2))
                else:
                    groups.append(dict(GOOD_GROUP_RESPONSE, group_id=g["group_id"]))
            return {"task_id": task["task_id"], "batch_id": task["batch_id"], "groups": groups}
        for _ in range(2):
            task = runtime.next_task(sid)
            runtime.submit(sid, task["task_id"], response_for(task))
        task = runtime.next_task(sid)
        assert task["task_type"] == "PASS_B_CONSOLIDATE"
        stop_sig = GOOD_GROUP_RESPONSE["motifs"][0]["behavior_signature"]
        pass_b = {
            "task_id": task["task_id"],
            "canonical_motifs": [
                {"label": "add-stop-conditions",
                 "display_name": "Add stop conditions",
                 "invariant": "Introduces a stop condition triggered by repeated failed fix attempts.",
                 "behavior_signature": stop_sig,
                 "supporting_groups": [1, 3, 4, 5, 6, 7, 8],
                 "rejected_near_misses": [2]},
            ],
        }
        runtime.submit(sid, pass_b["task_id"], pass_b)
        task = runtime.next_task(sid)
        assert task["task_type"] == "VERIFY_MOTIF"
        decisions = [{"group_id": g["group_id"], "decision": "YES",
                      "reason": "stop conditions present", "confidence": 0.95}
                     for g in task["groups"]]
        runtime.submit(sid, task["task_id"],
                       {"task_id": task["task_id"], "motif_label": task["motif_label"],
                        "decisions": decisions})
        task = runtime.next_task(sid)
        assert task["task_type"] == "FINAL_REPORT"
        assert task["accepted_motifs"][0]["group_count"] == 7
        assert task["accepted_motifs"][0]["repository_count"] == 7
        report_md = "\n".join([
            "# Study", "## Target Skill", "x", "## Corpus summary", "y",
            "## Recurring adaptations", "z", "## Notable one-offs", "w",
            "## Caveats", "c",
        ])
        result = runtime.submit(sid, task["task_id"],
                                {"task_id": task["task_id"], "report_md": report_md})
        assert result["state"] == "COMPLETE"
        assert runtime.next_task(sid)["task_type"] == "COMPLETE"
        report_json = json.loads((runtime.store.base / sid / "report.json").read_text(encoding="utf-8"))
        assert report_json["accepted_motifs"][0]["supporting_groups"][0]["direct_skill_url"].startswith("https://github.com/")


class TestIdempotencyAndConflicts:
    def test_identical_duplicate_is_idempotent(self, runtime) -> None:
        start = runtime.start(URL)
        sid = start["study_id"]
        response = _pass_a_response_for(runtime, sid)
        task_id = response["task_id"]
        first = runtime.submit(sid, task_id, response)
        second = runtime.submit(sid, task_id, response)
        assert first["status"] == "ACCEPTED"
        assert second["status"] == "IDEMPOTENT"

    def test_conflicting_duplicate_rejected_without_force(self, runtime) -> None:
        start = runtime.start(URL)
        sid = start["study_id"]
        response = _pass_a_response_for(runtime, sid)
        task_id = response["task_id"]
        runtime.submit(sid, task_id, response)
        conflicting = json.loads(json.dumps(response))
        conflicting["groups"][0]["notes"] = "changed"
        with pytest.raises(T.SubmissionError):
            runtime.submit(sid, task_id, conflicting)
        with pytest.raises(T.SubmissionError):
            runtime.submit(sid, task_id, conflicting, force=False)

    def test_force_overrides_conflict(self, runtime) -> None:
        start = runtime.start(URL)
        sid = start["study_id"]
        response = _pass_a_response_for(runtime, sid)
        task_id = response["task_id"]
        runtime.submit(sid, task_id, response)
        conflicting = json.loads(json.dumps(response))
        conflicting["groups"][0]["notes"] = "changed"
        result = runtime.submit(sid, task_id, conflicting, force=True)
        assert result["status"] == "ACCEPTED"


class TestMalformedSubmissions:
    def test_unknown_group_rejected(self, runtime) -> None:
        start = runtime.start(URL)
        sid = start["study_id"]
        task = runtime.next_task(sid)
        response = _pass_a_response_for(runtime, sid)
        response["groups"][0]["group_id"] = 999
        with pytest.raises(T.SubmissionError):
            runtime.submit(sid, task["task_id"], response)
        state = runtime.store.load(sid)
        assert state.manifest["counts"]["groups_analyzed"] == 0

    def test_bad_enum_rejected(self, runtime) -> None:
        start = runtime.start(URL)
        sid = start["study_id"]
        task = runtime.next_task(sid)
        response = _pass_a_response_for(runtime, sid)
        response["groups"][0]["meaningful_behavior_change"] = "MAYBE"
        with pytest.raises(T.SubmissionError):
            runtime.submit(sid, task["task_id"], response)

    def test_missing_invariant_rejected(self, runtime) -> None:
        start = runtime.start(URL)
        sid = start["study_id"]
        task = runtime.next_task(sid)
        response = _pass_a_response_for(runtime, sid)
        response["groups"][0]["motifs"][0]["invariant"] = ""
        with pytest.raises(T.SubmissionError):
            runtime.submit(sid, task["task_id"], response)

    def test_vague_invariant_rejected(self, runtime) -> None:
        start = runtime.start(URL)
        sid = start["study_id"]
        task = runtime.next_task(sid)
        response = _pass_a_response_for(runtime, sid)
        response["groups"][0]["motifs"][0]["invariant"] = "Improves the workflow with more structure"
        with pytest.raises(T.SubmissionError):
            runtime.submit(sid, task["task_id"], response)

    def test_malformed_does_not_advance_state(self, runtime) -> None:
        start = runtime.start(URL)
        sid = start["study_id"]
        task = runtime.next_task(sid)
        response = _pass_a_response_for(runtime, sid)
        response["groups"][0]["group_id"] = 999
        with pytest.raises(T.SubmissionError):
            runtime.submit(sid, task["task_id"], response)
        assert runtime.store.load(sid).status == "PASS_A_IN_PROGRESS"


class TestResumeAndSampling:
    def test_resume_after_one_batch(self, runtime) -> None:
        start = runtime.start(URL)
        sid = start["study_id"]
        task = runtime.next_task(sid)
        assert task["task_type"] == "PASS_A_BATCH"
        runtime.submit(sid, task["task_id"], _pass_a_response_for(runtime, sid))
        # interrupt: new runtime instance over the same base dir
        revived = StudyRuntime(base_dir=runtime.base_dir,
                               evidence_builder=runtime._evidence_builder,
                               batch_size=4)
        state = revived.store.load(sid)
        assert state.manifest["counts"]["groups_analyzed"] == 4
        task = revived.next_task(sid)
        assert task["task_type"] == "PASS_A_BATCH"
        # remaining batch only
        assert task["batch_id"] == "pass-a-002"

    def test_sampling_applied_above_limit(self, tmp_path) -> None:
        big = _fake_evidence(n_extra_groups=MAX_SEMANTIC_GROUPS)  # 2 + 250
        rt = StudyRuntime(base_dir=tmp_path, evidence_builder=lambda url: big)
        result = rt.start(URL)
        state = rt.store.load(result["study_id"])
        assert state.manifest["sampling_applied"] is True
        assert state.manifest["semantic_groups_analyzed"] == MAX_SEMANTIC_GROUPS
        assert state.manifest["total_groups_available"] == MAX_SEMANTIC_GROUPS + 2

    def test_no_sampling_below_limit(self, runtime) -> None:
        result = runtime.start(URL)
        state = runtime.store.load(result["study_id"])
        assert state.manifest.get("sampling_applied") is False


class TestCliSurface:
    def test_cli_commands_registered(self) -> None:
        result = CliRunner().invoke(app, ["--help"])
        for command in ("study-start", "study-status", "study-next",
                        "study-submit", "study-report"):
            assert command in result.output

    def test_study_start_json(self, tmp_path) -> None:
        import skillvariants.cli as cli_mod
        original = cli_mod._runtime

        def fake_runtime(base_dir=None, batch_size=8):
            return StudyRuntime(base_dir=tmp_path,
                                evidence_builder=lambda url: _fake_evidence(),
                                batch_size=batch_size)

        cli_mod._runtime = fake_runtime
        try:
            result = CliRunner().invoke(app, ["study-start", URL])
            assert result.exit_code == 0, result.output
            payload = json.loads(result.output)
            assert payload["status"] == "EVIDENCE_READY"
        finally:
            cli_mod._runtime = original
