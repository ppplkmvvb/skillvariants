"""Study runtime state machine (spec sections 5-23).

Orchestrates: study creation, evidence collection, deterministic PASS A
batching, task dispatch, validated submissions with idempotency, PASS B +
guardrail integration, deterministic motif artifact, and final report.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..consolidation import (
    BehaviorSignature,
    ClusterDecision,
    ProposedCluster,
    accept_cluster,
    precheck_cluster,
)
from .models import (
    DEFAULT_BATCH_SIZE,
    MAX_SEMANTIC_GROUPS,
    MAX_SPLIT_ITERATIONS,
    StudyState,
    atomic_write_json,
)
from .storage import StudyStore
from . import tasks as T
from . import reporting as R


class StudyRuntime:
    def __init__(self, base_dir: Path | None = None,
                 evidence_builder=None, batch_size: int = DEFAULT_BATCH_SIZE) -> None:
        self.store = StudyStore(base_dir)
        self.base_dir = base_dir
        self._evidence_builder = evidence_builder
        self.batch_size = max(4, min(12, batch_size))

    # ---- evidence ---------------------------------------------------------
    def _collect_evidence(self, url: str, cache_dir: Path | None) -> dict:
        if self._evidence_builder is not None:
            return self._evidence_builder(url)
        from ..cli_helpers import build_evidence_payload
        return build_evidence_payload(url, cache_dir)

    # ---- study-start --------------------------------------------------------
    def start(self, url: str, cache_dir: Path | None = None) -> dict:
        evidence = self._collect_evidence(url, cache_dir)
        target = evidence["target"]
        content_hash = target["normalized_hash"]
        existing = self.store.find_by_target(target, content_hash)
        if existing:
            return {
                "study_id": existing, "resumed": True,
                "status": self.store.load(existing).manifest["status"],
            }
        stale = self.store.find_any_for_target(target)
        all_groups = evidence["groups"]
        total_available = len(all_groups)
        sampling_applied = total_available > MAX_SEMANTIC_GROUPS
        if sampling_applied:
            step = len(all_groups) / MAX_SEMANTIC_GROUPS
            semantic_groups = [all_groups[min(len(all_groups) - 1, round(i * step))]
                               for i in range(MAX_SEMANTIC_GROUPS)]
        else:
            semantic_groups = all_groups
        scoped_evidence = {**evidence, "groups": semantic_groups,
                           "total_groups_available": total_available}
        if stale:
            scoped_evidence["superseded_study_id"] = stale
        study_id, state = self.store.create(
            target, content_hash, scoped_evidence,
            [g["group_id"] for g in semantic_groups], sampling_applied)
        if stale:
            self.store.append_event(study_id, "TARGET_CHANGED", {"previous_study": stale})
            state.set_status("TARGET_CHANGED" if False else state.status)
        return {"study_id": study_id, "resumed": False, "status": state.status}

    # ---- study-status -------------------------------------------------------
    def status(self, study_id: str) -> dict:
        state = self.store.load(study_id)
        return {
            "study_id": study_id,
            "status": state.status,
            "target": state.manifest["target"],
            "counts": state.manifest["counts"],
            "sampling_applied": state.manifest.get("sampling_applied", False),
            "errors": state.manifest.get("errors", []),
        }

    # ---- study-next -----------------------------------------------------------
    def next_task(self, study_id: str) -> dict:
        state = self.store.load(study_id)
        if state.status == "COMPLETE":
            return {"task_type": "COMPLETE", "study_id": study_id,
                    "report_path": str(self.store.base / study_id / "report.md")}
        if state.status in ("FAILED_TERMINAL", "TARGET_CHANGED"):
            return {"task_type": "COMPLETE", "study_id": study_id,
                    "status": state.status,
                    "note": "study cannot advance; see manifest.errors"}

        if state.status in ("CREATED", "EVIDENCE_READY"):
            state.set_status("PASS_A_IN_PROGRESS")
            self.store.save_manifest(study_id, state)

        if state.status == "PASS_A_IN_PROGRESS":
            return self._next_pass_a_task(study_id, state)

        if state.status in ("PASS_A_COMPLETE", "PASS_B_READY"):
            if state.pass_b is None:
                state.set_status("PASS_B_READY")
                self.store.save_manifest(study_id, state)
                return T.build_pass_b_task(
                    "pass-b-001", list(state.pass_a.values()))
            state.set_status("VERIFYING")
            self.store.save_manifest(study_id, state)

        if state.status == "VERIFYING":
            return self._next_verify_task(study_id, state)

        if state.status == "PASS_B_COMPLETE":
            state.set_status("VERIFYING")
            self.store.save_manifest(study_id, state)
            return self._next_verify_task(study_id, state)

        return {"task_type": "COMPLETE", "study_id": study_id,
                "report_path": str(self.store.base / study_id / "report.md")}

    # ---- PASS A batching ------------------------------------------------------
    def _pending_batches(self, state: StudyState) -> list[list[int]]:
        group_ids = sorted(g["group_id"] for g in state.evidence["groups"])
        size = self.batch_size
        batches = [group_ids[i:i + size] for i in range(0, len(group_ids), size)]
        done = {b["batch_id"] for b in state.batches.values()
                if b.get("status") == "SUBMITTED"}
        pending = []
        for index, gids in enumerate(batches, start=1):
            batch_id = f"pass-a-{index:03d}"
            if batch_id not in done:
                pending.append((batch_id, gids))
        return pending

    def _next_pass_a_task(self, study_id: str, state: StudyState) -> dict:
        pending = self._pending_batches(state)
        if not pending:
            state.set_status("PASS_A_COMPLETE")
            self.store.save_manifest(study_id, state)
            return self.next_task(study_id)
        batch_id, gids = pending[0]
        by_id = {g["group_id"]: g for g in state.evidence["groups"]}
        payload_groups = []
        for gid in gids:
            g = dict(by_id[gid])
            g["compare_command"] = (
                f"uvx skillvariants compare "
                f"{state.manifest['target']['direct_skill_url']} "
                f"{g['direct_skill_url']} --json")
            payload_groups.append(g)
        task = T.build_pass_a_batch_task(f"pass-a-{batch_id.split('-')[-1]}", batch_id, payload_groups)
        state.batches[batch_id] = {"batch_id": batch_id, "group_ids": gids, "status": "DISPATCHED"}
        atomic_write_json(self.store.base / study_id / "batches.json", state.batches)
        self.store.append_event(study_id, "PASS_A_BATCH_DISPATCHED",
                                {"batch_id": batch_id, "groups": len(gids)})
        return task

    # ---- study-submit ----------------------------------------------------------
    def submit(self, study_id: str, task_id: str, response: dict,
               force: bool = False) -> dict:
        state = self.store.load(study_id)
        fingerprint = __import__("hashlib").sha256(
            json.dumps(response, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        previous = state.fingerprints.get(task_id)
        if previous is not None:
            if previous == fingerprint:
                self.store.append_event(study_id, "IDEMPOTENT_RESUBMIT", {"task_id": task_id})
                return {"status": "IDEMPOTENT", "task_id": task_id}
            if not force:
                raise T.SubmissionError(
                    f"conflicting resubmission for {task_id}; use --force to override")

        if task_id.startswith("pass-a-"):
            batch_id = "pass-a-" + task_id.split("-")[-1]
            batch_info = state.batches.get(batch_id)
            if batch_info is None:
                raise T.SubmissionError(f"unknown batch {batch_id}")
            if batch_info.get("status") == "SUBMITTED" and not force:
                raise T.SubmissionError(f"batch {batch_id} already submitted")
            task = self._rebuild_pass_a_task(batch_id, batch_info, state)
            validated = T.validate_pass_a_response(task, response)
            self.store.save_pass_a_batch(study_id, batch_id,
                                         batch_info["group_ids"], response)
            self.store.merge_pass_a(study_id, state, validated)
            state.batches[batch_id]["status"] = "SUBMITTED"
            atomic_write_json(self.store.base / study_id / "batches.json", state.batches)
            self.store.record_fingerprint(study_id, state, task_id, response)
            pending = self._pending_batches(state)
            if not pending:
                state.set_status("PASS_A_COMPLETE")
            self.store.save_manifest(study_id, state)
            self.store.append_event(study_id, "PASS_A_BATCH_SUBMITTED",
                                    {"batch_id": batch_id, "groups": len(validated),
                                     "escalations": sum(1 for v in validated
                                                        if v["needs_source_escalation"])})
            return {"status": "ACCEPTED", "task_id": task_id,
                    "groups_analyzed": state.manifest["counts"]["groups_analyzed"],
                    "next_state": state.status}

        if task_id.startswith("pass-b-"):
            if state.status not in ("PASS_A_COMPLETE", "PASS_B_READY"):
                raise T.SubmissionError("PASS B submitted before PASS A completion")
            task = T.build_pass_b_task(task_id, list(state.pass_a.values()))
            validated = T.validate_pass_b_response(task, response)
            self.store.save_pass_b(study_id, {"task_id": task_id, "canonical_motifs": validated})
            self.store.record_fingerprint(study_id, state, task_id, response)
            state.pass_b = {"canonical_motifs": validated}
            state.manifest["counts"]["motifs_proposed"] = len(validated)
            state.set_status("PASS_B_COMPLETE")
            self.store.save_manifest(study_id, state)
            self.store.append_event(study_id, "PASS_B_SUBMITTED",
                                    {"canonical_motifs": len(validated)})
            return {"status": "ACCEPTED", "task_id": task_id,
                    "canonical_motifs": len(validated), "next_state": state.status}

        if task_id.startswith("verify-"):
            motif_label = response.get("motif_label")
            proposed = self._find_proposed(state, motif_label)
            if proposed is None:
                raise T.SubmissionError(f"unknown motif {motif_label!r}")
            task = self._rebuild_verify_task(motif_label, proposed, state)
            validated = T.validate_verifier_response(task, response)
            self.store.save_verification(study_id, motif_label, validated)
            self.store.record_fingerprint(study_id, state, task_id, response)
            state.verification[motif_label] = validated
            self.store.append_event(study_id, "VERIFIER_SUBMITTED",
                                    {"motif": motif_label, "decisions": len(validated)})
            motifs = self._finalize_motifs(study_id, state)
            self.store.save_manifest(study_id, state)
            return {"status": "ACCEPTED", "task_id": task_id,
                    "motifs_accepted": motifs["accepted_count"],
                    "next_state": state.status}

        if task_id.startswith("final-report-"):
            required_ok = self._validate_report(response)
            if not required_ok:
                raise T.SubmissionError(
                    "report.md missing required sections: "
                    + ", ".join(s for s in self._missing_sections(response)))
            self.store.save_report_md(study_id, response.get("report_md", ""))
            report_json = self._report_json(state)
            self.store.save_report_json(study_id, report_json)
            self.store.record_fingerprint(study_id, state, task_id, response)
            state.set_status("COMPLETE")
            self.store.save_manifest(study_id, state)
            self.store.append_event(study_id, "STUDY_COMPLETE", {})
            return {"status": "ACCEPTED", "task_id": task_id, "state": "COMPLETE"}

        raise T.SubmissionError(f"unknown task_id: {task_id!r}")

    # ---- verifier orchestration -------------------------------------------------
    def _next_verify_task(self, study_id: str, state: StudyState) -> dict:
        index = 0
        for motif in state.pass_b["canonical_motifs"]:
            if len(motif["supporting_groups"]) < 3:
                continue  # deterministic recurrence floor handled by engine
            label = motif["label"]
            index += 1
            if label in state.verification:
                continue
            return self._rebuild_verify_task(label, motif, state,
                                             task_id=f"verify-{index:03d}")
        # all motifs verified -> finalize
        motifs = self._finalize_motifs(study_id, state)
        if motifs["accepted_count"] == 0:
            state.set_status("COMPLETE")
            self.store.save_manifest(study_id, state)
            self.store.append_event(study_id, "STUDY_COMPLETE_NO_MOTIFS", {})
            return {"task_type": "COMPLETE", "study_id": study_id,
                    "note": "no motif passed the guardrail; report is optional",
                    "report_path": str(self.store.base / study_id / "report.md")}
        return self._final_report_task(study_id, state, motifs)

    def _find_proposed(self, state: StudyState, label: str):
        for motif in state.pass_b["canonical_motifs"]:
            if motif["label"] == label:
                return motif
        return None

    def _rebuild_verify_task(self, label: str, motif: dict, state: StudyState,
                             task_id: str | None = None) -> dict:
        by_id = {g["group_id"]: g for g in state.evidence["groups"]}
        payloads = []
        for gid in motif["supporting_groups"]:
            g = dict(by_id[gid])
            g["compare_command"] = (
                f"uvx skillvariants compare "
                f"{state.manifest['target']['direct_skill_url']} "
                f"{g['direct_skill_url']} --json")
            payloads.append(g)
        index = 0
        for m in state.pass_b["canonical_motifs"]:
            if len(m["supporting_groups"]) < 3:
                continue
            index += 1
            if m["label"] == label:
                break
        task_id = task_id or f"verify-{index:03d}"
        return T.build_verify_task(task_id, motif, payloads)

    def _rebuild_pass_a_task(self, batch_id: str, batch_info: dict,
                             state: StudyState) -> dict:
        by_id = {g["group_id"]: g for g in state.evidence["groups"]}
        payload_groups = []
        for gid in batch_info["group_ids"]:
            g = dict(by_id[gid])
            g["compare_command"] = (
                f"uvx skillvariants compare "
                f"{state.manifest['target']['direct_skill_url']} "
                f"{g['direct_skill_url']} --json")
            payload_groups.append(g)
        return T.build_pass_a_batch_task(batch_id.replace("pass-a-", "pass-a-"),
                                         batch_id, payload_groups)

    # ---- deterministic motif artifact --------------------------------------------
    def _finalize_motifs(self, study_id: str, state: StudyState) -> dict:
        by_id = {g["group_id"]: g for g in state.evidence["groups"]}
        accepted, suppressed = [], []
        target_url = state.manifest["target"]["direct_skill_url"]
        for motif in state.pass_b["canonical_motifs"]:
            label = motif["label"]
            raw_decisions = state.verification.get(label)
            if raw_decisions is None:
                suppressed.append({"label": label, "status": "UNVERIFIED"})
                continue
            from ..consolidation import ClusterDecision as _CD
            decisions = [
                d if isinstance(d, _CD) else _CD(
                    group_id=d["group_id"], decision=d["decision"],
                    reason=d.get("reason", ""),
                    confidence=d.get("confidence", 0.0))
                for d in raw_decisions
            ]
            proposed = ProposedCluster(
                label=label, invariant=motif["invariant"],
                signature=BehaviorSignature.from_dict(motif["behavior_signature"]),
                member_group_ids=[d.group_id for d in decisions],
            )
            problems = precheck_cluster(proposed)
            repos_map = {}
            for d in decisions:
                group = by_id.get(d.group_id)
                if group:
                    repos_map[d.group_id] = group["repository"]
            result = accept_cluster(proposed, decisions, repos_map)
            entry = {
                "label": label,
                "display_name": motif.get("display_name", label.replace("-", " ")),
                "invariant": motif["invariant"],
                "behavior_signature": motif["behavior_signature"],
                "status": result.status,
                "rejection_rate": result.rejection_rate,
                "group_count": result.verified_yes_groups,
                "repository_count": result.verified_yes_repos,
                "supporting_groups": [
                    {"group_id": gid,
                     **({"repository": by_id[gid]["repository"],
                         "path": by_id[gid]["path"],
                         "ref": by_id[gid]["ref"],
                         "direct_skill_url": by_id[gid]["direct_skill_url"]}
                        if gid in by_id else {})}
                    for gid in (d.group_id for d in decisions
                                if d.decision == "YES")
                ],
            }
            if result.accepted:
                accepted.append(entry)
            else:
                suppressed.append({**entry, "uncertain": result.uncertain_group_ids,
                                   "rejected": result.rejected_group_ids})
        state.manifest["counts"]["motifs_verified"] = sum(
            1 for m in state.pass_b["canonical_motifs"]
            if m["label"] in state.verification)
        state.manifest["counts"]["motifs_accepted"] = len(accepted)
        motifs = {"accepted_count": len(accepted), "accepted": accepted,
                  "suppressed": suppressed}
        self.store.save_motifs(study_id, motifs)
        self.store.append_event(study_id, "MOTIFS_FINALIZED",
                                {"accepted": len(accepted),
                                 "suppressed": len(suppressed)})
        return motifs

    # ---- final report --------------------------------------------------------------
    def _final_report_task(self, study_id: str, state: StudyState,
                           motifs: dict) -> dict:
        task_id = f"final-report-{state.manifest['counts']['motifs_accepted']:03d}"
        return {
            "task_id": task_id,
            "task_type": "FINAL_REPORT",
            "instructions": (
                "Write report.md with the required sections using ONLY the "
                "accepted motifs and deterministic summary provided. Follow "
                "the three-level interpretation discipline. Submit "
                "{\"task_id\": ..., \"report_md\": \"...\"}."
            ),
            "study_summary": {
                "target": state.manifest["target"],
                "counts": state.manifest["counts"],
                "sampling_applied": state.manifest.get("sampling_applied", False),
            },
            "accepted_motifs": motifs["accepted"],
            "suppressed_motifs": [
                {"label": s["label"], "status": s["status"]}
                for s in motifs["suppressed"]
            ],
            "required_sections": [
                "Target Skill", "Corpus summary", "Recurring adaptations",
                "Notable one-offs", "Caveats",
            ],
        }

    def _missing_sections(self, response: dict) -> list[str]:
        return R.missing_sections(response.get("report_md", ""))

    def _validate_report(self, response: dict) -> bool:
        return not self._missing_sections(response)

    def _report_json(self, state: StudyState) -> dict:
        motifs = json.loads((self.store.base / state.manifest["study_id"]
                             / "motifs.json").read_text(encoding="utf-8"))
        return R.build_report_json(
            state.manifest["study_id"], state.manifest["target"],
            state.manifest["counts"], motifs,
            state.manifest.get("sampling_applied", False))
