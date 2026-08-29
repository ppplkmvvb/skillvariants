"""Task payload construction and response validation (spec sections 8-16)."""
from __future__ import annotations

from ..consolidation import validate_invariant
from .models import (
    MAX_VERIFIER_GROUPS_PER_TASK,
    MEANINGFUL_VALUES,
    VERIFIER_DECISIONS,
)


class SubmissionError(ValueError):
    """Malformed or conflicting agent submission; study must not advance."""


# ---- PASS A -----------------------------------------------------------------

def build_pass_a_batch_task(task_id: str, batch_id: str, groups: list[dict]) -> dict:
    return {
        "task_id": task_id,
        "task_type": "PASS_A_BATCH",
        "batch_id": batch_id,
        "batch_size": len(groups),
        "instructions": (
            "For each group decide meaningful_behavior_change (YES/PARTIAL/NO) "
            "and propose 0-3 concrete action motifs. Analyze groups "
            "independently; do not assume other groups exist. If the excerpts "
            "are insufficient, set needs_source_escalation=true with a reason "
            "and use compare_command or the direct source URL."
        ),
        "groups": groups,
    }


def validate_pass_a_response(task: dict, response: dict) -> list[dict]:
    if response.get("task_id") != task["task_id"]:
        raise SubmissionError(
            f"task_id mismatch: expected {task['task_id']}, "
            f"got {response.get('task_id')!r}")
    if response.get("batch_id") != task["batch_id"]:
        raise SubmissionError("batch_id mismatch")
    batch_groups = {g["group_id"]: g for g in task["groups"]}
    submitted = response.get("groups")
    if not isinstance(submitted, list) or not submitted:
        raise SubmissionError("response.groups must be a non-empty list")
    seen = set()
    validated = []
    for group in submitted:
        gid = group.get("group_id")
        if gid not in batch_groups:
            raise SubmissionError(f"unknown group_id {gid!r} for this batch")
        if gid in seen:
            raise SubmissionError(f"duplicate group_id {gid} in response")
        seen.add(gid)
        meaningful = group.get("meaningful_behavior_change")
        if meaningful not in MEANINGFUL_VALUES:
            raise SubmissionError(
                f"group {gid}: meaningful_behavior_change must be one of "
                f"{MEANINGFUL_VALUES}")
        motifs = group.get("motifs", [])
        if not isinstance(motifs, list):
            raise SubmissionError(f"group {gid}: motifs must be a list")
        clean_motifs = []
        for motif in motifs:
            action = (motif.get("action") or "").strip()
            invariant = (motif.get("invariant") or "").strip()
            if not action:
                raise SubmissionError(f"group {gid}: motif action required")
            ok, reason = validate_invariant(invariant)
            if not ok:
                raise SubmissionError(f"group {gid}: motif {action!r}: {reason}")
            clean_motifs.append({
                "action": action,
                "invariant": invariant,
                "behavior_signature": _validated_signature(
                    gid, motif.get("behavior_signature")),
                "evidence_summary": (motif.get("evidence_summary") or "")[:400],
                "confidence": _confidence(motif.get("confidence")),
            })
        validated.append({
            "group_id": gid,
            "meaningful_behavior_change": meaningful,
            "motifs": clean_motifs,
            "needs_source_escalation": bool(group.get("needs_source_escalation")),
            "escalation_reason": (group.get("reason") or "")[:300],
            "notes": (group.get("notes") or "")[:400],
        })
    return validated


def _validated_signature(gid, signature) -> dict:
    if not isinstance(signature, dict):
        raise SubmissionError(f"group {gid}: behavior_signature object required")
    return {
        "trigger": (signature.get("trigger") or None),
        "action": (signature.get("action") or None),
        "object": (signature.get("object") or None),
        "outcome": (signature.get("outcome") or None),
    }


def _confidence(value) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        raise SubmissionError("confidence must be a number")
    if not 0.0 <= confidence <= 1.0:
        raise SubmissionError("confidence must be within [0, 1]")
    return round(confidence, 3)


# ---- PASS B -----------------------------------------------------------------

def build_pass_b_task(task_id: str, pass_a_groups: list[dict]) -> dict:
    proposals = []
    for group in pass_a_groups:
        for motif in group["motifs"]:
            proposals.append({
                "group_id": group["group_id"],
                "action": motif["action"],
                "invariant": motif["invariant"],
                "behavior_signature": motif["behavior_signature"],
                "evidence_summary": motif["evidence_summary"],
            })
    return {
        "task_id": task_id,
        "task_type": "PASS_B_CONSOLIDATE",
        "instructions": (
            "Cluster the proposed motif actions by BEHAVIOR equivalence, not "
            "topic similarity. Every supporting group must be truthfully "
            "described by the same concrete behavioral invariant. Provide one "
            "strict invariant and a behavior signature per canonical motif; "
            "list rejected near-misses. Do not compute recurrence — the "
            "engine owns counts."
        ),
        "proposals": proposals,
    }


def validate_pass_b_response(task: dict, response: dict) -> list[dict]:
    if response.get("task_id") != task["task_id"]:
        raise SubmissionError("task_id mismatch for PASS_B_CONSOLIDATE")
    motifs = response.get("canonical_motifs")
    if not isinstance(motifs, list):
        raise SubmissionError("canonical_motifs must be a list")
    known_groups = {g["group_id"] for g in task["proposals"]}
    validated = []
    for motif in motifs:
        label = (motif.get("label") or "").strip()
        if not label:
            raise SubmissionError("canonical motif label required")
        ok, reason = validate_invariant(motif.get("invariant") or "")
        if not ok:
            raise SubmissionError(f"motif {label!r}: invariant {reason}")
        supporting = motif.get("supporting_groups", [])
        if not isinstance(supporting, list):
            raise SubmissionError(f"motif {label!r}: supporting_groups must be a list")
        unknown = [gid for gid in supporting if gid not in known_groups]
        if unknown:
            raise SubmissionError(
                f"motif {label!r}: unknown group ids {unknown[:5]}")
        validated.append({
            "label": label,
            "display_name": (motif.get("display_name") or label.replace("-", " ")),
            "invariant": motif["invariant"].strip(),
            "behavior_signature": _validated_signature(label, motif.get("behavior_signature")),
            "supporting_groups": list(dict.fromkeys(supporting)),
            "rejected_near_misses": list(motif.get("rejected_near_misses", [])),
        })
    return validated


# ---- verifier -----------------------------------------------------------------

def build_verify_task(task_id: str, motif: dict, group_payloads: list[dict]) -> dict:
    candidates = group_payloads[:MAX_VERIFIER_GROUPS_PER_TASK]
    return {
        "task_id": task_id,
        "task_type": "VERIFY_MOTIF",
        "motif_label": motif["label"],
        "invariant": motif["invariant"],
        "behavior_signature": motif["behavior_signature"],
        "instructions": (
            "For each group decide YES/NO/UNCERTAIN: does this group's "
            "evidence satisfy the invariant? Judge only this group. UNCERTAIN "
            "groups are excluded from recurrence."
        ),
        "groups": candidates,
    }


def validate_verifier_response(task: dict, response: dict) -> list[dict]:
    if response.get("task_id") != task["task_id"]:
        raise SubmissionError("task_id mismatch for VERIFY_MOTIF")
    if response.get("motif_label") != task["motif_label"]:
        raise SubmissionError("motif_label mismatch for VERIFY_MOTIF")
    decisions = response.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        raise SubmissionError("decisions must be a non-empty list")
    expected = {g["group_id"] for g in task["groups"]}
    seen = set()
    validated = []
    for decision in decisions:
        gid = decision.get("group_id")
        if gid not in expected:
            raise SubmissionError(f"unknown group_id {gid!r} for this motif")
        if gid in seen:
            raise SubmissionError(f"duplicate group_id {gid} in decisions")
        seen.add(gid)
        verdict = decision.get("decision")
        if verdict not in VERIFIER_DECISIONS:
            raise SubmissionError(f"group {gid}: decision must be one of {VERIFIER_DECISIONS}")
        validated.append({
            "group_id": gid,
            "decision": verdict,
            "reason": (decision.get("reason") or "")[:300],
            "confidence": _confidence(decision.get("confidence")),
        })
    missing = expected - seen
    if missing:
        raise SubmissionError(f"missing verifier decisions for groups {sorted(missing)[:5]}")
    return validated
