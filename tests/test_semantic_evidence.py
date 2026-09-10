"""Claims must survive source citation checks before semantic consolidation."""
import copy

import pytest

from skillvariants.comparison import compare_documents
from skillvariants.parser import parse_skill_md
from skillvariants.study import tasks as T


def paired_case():
    a = parse_skill_md("---\nname: approval\n---\n# Review\nProceed with implementation.\n")
    b = parse_skill_md("---\nname: approval\n---\n# Review\nWait for explicit approval.\nProceed with implementation.\n")
    comparison = compare_documents(a, b)
    group = {"group_id": 1, "comparison": comparison}
    evidence = {side: {"hunk_id": "hunk-001", "start_line": 5, "end_line": 5,
                       "quote": text, "raw_sha256": comparison["sources"][side]["raw_sha256"]}
                for side, text in (("a", "Proceed with implementation."),
                                   ("b", "Wait for explicit approval."))}
    motif = {"action": "Require explicit approval", "change_type": "ADDED",
             "invariant": "Adds a requirement to wait for explicit approval before implementation.",
             "behavior_signature": {"trigger": "before implementation", "action": "wait for approval",
                                    "object": "implementation", "outcome": "approval precedes execution"},
             "evidence": evidence, "evidence_summary": "The candidate inserts an approval requirement.",
             "confidence": .9}
    task = T.build_pass_a_batch_task("pass-a-001", "pass-a-001", [group])
    response = {"task_id": task["task_id"], "batch_id": task["batch_id"], "groups": [{
        "group_id": 1, "meaningful_behavior_change": "YES", "motifs": [motif],
        "needs_source_escalation": False, "notes": "Paired source checked."}]}
    return task, response


@pytest.mark.parametrize("field", ["change_type", "evidence"])
def test_semantic_claim_requires_direction_and_paired_evidence(field):
    task, response = paired_case()
    response["groups"][0]["motifs"][0].pop(field)
    with pytest.raises(T.SubmissionError, match=field):
        T.validate_pass_a_response(task, response)


@pytest.mark.parametrize("field,value", [
    ("quote", "A fabricated line that never appeared."),
    ("raw_sha256", "f" * 64),
    ("hunk_id", "hunk-999"),
    ("start_line", 500),
    ("start_line", True),
])
def test_citation_must_match_source_hash_hunk_and_exact_lines(field, value):
    task, response = paired_case()
    response["groups"][0]["motifs"][0]["evidence"]["b"][field] = value
    with pytest.raises(T.SubmissionError, match="evidence"):
        T.validate_pass_a_response(task, response)


def test_valid_citations_and_direction_are_retained_for_later_stages():
    task, response = paired_case()
    validated = T.validate_pass_a_response(task, response)
    original = response["groups"][0]["motifs"][0]
    assert validated[0]["motifs"][0]["evidence"] == original["evidence"]
    assert validated[0]["motifs"][0]["change_type"] == "ADDED"
    assert T.build_pass_b_task("pass-b-001", validated)["proposals"][0]["evidence"] == original["evidence"]


def test_unresolved_source_does_not_contribute_motifs():
    task, response = paired_case()
    group = response["groups"][0]
    group["needs_source_escalation"] = True
    group["reason"] = "Full source was not available."
    with pytest.raises(T.SubmissionError, match="escalation"):
        T.validate_pass_a_response(task, response)
    group["motifs"] = []
    group["meaningful_behavior_change"] = "PARTIAL"
    assert T.validate_pass_a_response(task, response)[0]["needs_source_escalation"] is True


def test_unchanged_rule_is_excluded_from_adaptation_proposals():
    task, response = paired_case()
    group = response["groups"][0]
    group["meaningful_behavior_change"] = "NO"
    motif = group["motifs"][0]
    motif["change_type"] = "UNCHANGED"
    motif["evidence"]["b"].update(start_line=6, end_line=6, quote="Proceed with implementation.")
    validated = T.validate_pass_a_response(task, response)
    assert T.build_pass_b_task("pass-b-001", validated)["proposals"] == []


def test_identical_cited_rule_cannot_be_called_added():
    task, response = paired_case()
    motif = response["groups"][0]["motifs"][0]
    motif["evidence"]["b"].update(start_line=6, end_line=6, quote="Proceed with implementation.")
    with pytest.raises(T.SubmissionError, match="unchanged|identical"):
        T.validate_pass_a_response(task, response)


def test_truncated_evidence_cannot_support_an_unqualified_addition():
    task, response = paired_case()
    task["groups"][0]["comparison"]["truncation"]["truncated"] = True
    with pytest.raises(T.SubmissionError, match="truncated|escalat"):
        T.validate_pass_a_response(task, response)


def test_truncated_comparison_can_escalate_to_hash_checked_full_snapshots(tmp_path):
    task, response = paired_case()
    comparison = task["groups"][0]["comparison"]
    comparison["truncation"]["truncated"] = True
    texts = {"a": "---\nname: approval\n---\n# Review\nProceed with implementation.\n",
             "b": "---\nname: approval\n---\n# Review\nWait for explicit approval.\nProceed with implementation.\n"}
    for side, text in texts.items():
        path = tmp_path / f"{side}.md"
        path.write_bytes(text.encode("utf-8"))
        comparison["sources"][side]["snapshot_path"] = str(path)
        response["groups"][0]["motifs"][0]["evidence"][side]["hunk_id"] = "full-source"
    validated = T.validate_pass_a_response(task, response)
    assert validated[0]["motifs"][0]["evidence"]["a"]["hunk_id"] == "full-source"
    (tmp_path / "a.md").write_text("tampered", encoding="utf-8")
    with pytest.raises(T.SubmissionError, match="hash|snapshot"):
        T.validate_pass_a_response(task, response)


def test_consolidation_rejects_opposite_change_directions():
    task, response = paired_case()
    validated = T.validate_pass_a_response(task, response)
    second = copy.deepcopy(validated[0])
    second["group_id"] = 2
    second["motifs"][0]["change_type"] = "REMOVED"
    task_b = T.build_pass_b_task("pass-b-001", validated + [second])
    motif = response["groups"][0]["motifs"][0]
    proposed = {"task_id": task_b["task_id"], "canonical_motifs": [{
        "label": "approval", "change_type": "ADDED", "invariant": motif["invariant"],
        "behavior_signature": motif["behavior_signature"], "supporting_groups": [1, 2]}]}
    with pytest.raises(T.SubmissionError, match="direction|change_type"):
        T.validate_pass_b_response(task_b, proposed)


def test_yes_verifier_decision_requires_its_own_checked_citations():
    task, response = paired_case()
    motif = response["groups"][0]["motifs"][0]
    verify = T.build_verify_task("verify-001", {**motif, "label": "approval"}, task["groups"])
    answer = {"task_id": verify["task_id"], "motif_label": "approval", "decisions": [{
        "group_id": 1, "decision": "YES", "reason": "The pair supports the addition.", "confidence": .9}]}
    with pytest.raises(T.SubmissionError, match="evidence"):
        T.validate_verifier_response(verify, answer)
    answer["decisions"][0]["evidence"] = motif["evidence"]
    assert T.validate_verifier_response(verify, answer)[0]["evidence"] == motif["evidence"]


@pytest.mark.parametrize("missing", [False, True])
def test_no_change_cannot_hide_incomplete_source_evidence(missing):
    task, response = paired_case()
    if missing:
        task["groups"][0].pop("comparison")
    else:
        task["groups"][0]["comparison"]["truncation"]["truncated"] = True
    group = response["groups"][0]
    group.update(meaningful_behavior_change="NO", motifs=[])
    with pytest.raises(T.SubmissionError, match="source|escalat"):
        T.validate_pass_a_response(task, response)
    group.update(needs_source_escalation=True, reason="Complete paired evidence unavailable.")
    assert T.validate_pass_a_response(task, response)[0]["needs_source_escalation"] is True


@pytest.mark.parametrize("field,value", [
    ("action", ["wait"]), ("invariant", {"rule": "wait"}),
    ("change_type", ["ADDED"]), ("evidence_summary", 42),
    ("behavior_signature", {"trigger": [], "action": "wait"}),
])
def test_malformed_nested_motif_returns_submission_error(field, value):
    task, response = paired_case()
    response["groups"][0]["motifs"][0][field] = value
    with pytest.raises(T.SubmissionError):
        T.validate_pass_a_response(task, response)
