"""Study runtime state machine (spec sections 5-23).

Orchestrates: study creation, evidence collection, deterministic PASS A
batching, task dispatch, validated submissions with idempotency, PASS B +
guardrail integration, deterministic motif artifact, and final report.
"""
from __future__ import annotations

import json
from functools import wraps
from pathlib import Path

from ..consolidation import (
    BehaviorSignature,
    ClusterDecision,
    ProposedCluster,
    accept_cluster,
    precheck_cluster,
    signatures_conflict,
)
from .models import (
    DEFAULT_BATCH_SIZE,
    MAX_SEMANTIC_GROUPS,
    MAX_VERIFIER_GROUPS_PER_TASK,
    SCHEMA_VERSION,
    RUNTIME_VERSION,
    StudyState,
    atomic_write_json,
    corpus_fingerprint,
    group_fingerprint_fields,
    response_fingerprint,
)
from .storage import StudyStore
from . import tasks as T
from . import reporting as R


def _transactional(method):
    @wraps(method)
    def invoke(self, study_id, *args, **kwargs):
        with self.store.transaction(study_id):
            return method(self, study_id, *args, **kwargs)
    return invoke


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
        all_groups = evidence["groups"]
        total_available = len(all_groups)
        sampling_applied = total_available > MAX_SEMANTIC_GROUPS
        if sampling_applied:
            all_groups = sorted(all_groups, key=lambda g: response_fingerprint(group_fingerprint_fields(g)))
            step = len(all_groups) / MAX_SEMANTIC_GROUPS
            semantic_groups = [all_groups[min(len(all_groups) - 1, round(i * step))]
                               for i in range(MAX_SEMANTIC_GROUPS)]
        else:
            semantic_groups = all_groups
        scoped_evidence = {**evidence, "groups": semantic_groups,
                           "total_groups_available": total_available}
        corpus_hash = corpus_fingerprint(evidence, semantic_groups)
        sid = self.store.study_id(target, content_hash, corpus_hash)
        with self.store.locked(sid):
            if self.store.exists(sid):
                state = self.store.load(sid)
                self._require_current_protocol(state)
                self._require_complete_artifacts(sid, state)
                return {"study_id": sid, "resumed": True, "status": state.status}
            return self._create_study(target, content_hash, scoped_evidence, semantic_groups,
                                      sampling_applied, corpus_hash)

    def _create_study(self, target, content_hash, scoped_evidence, semantic_groups,
                      sampling_applied, corpus_hash):
        stale = self.store.find_any_for_target(target)
        if stale:
            scoped_evidence["superseded_study_id"] = stale
        study_id, state = self.store.create(
            target, content_hash, scoped_evidence,
            [g["group_id"] for g in semantic_groups], sampling_applied,
            corpus_hash=corpus_hash, batch_size=self.batch_size)
        return {"study_id": study_id, "resumed": False, "status": state.status}

    # ---- study-status -------------------------------------------------------
    def status(self, study_id: str) -> dict:
        with self.store.locked(study_id):
            state = self.store.load(study_id)
            self._require_complete_artifacts(study_id, state)
            return {
                "study_id": study_id,
                "status": state.status,
                "target": state.manifest["target"],
                "counts": state.manifest["counts"],
                "sampling_applied": state.manifest.get("sampling_applied", False),
                "errors": state.manifest.get("errors", []),
            }

    # ---- study-next -----------------------------------------------------------
    @_transactional
    def next_task(self, study_id: str) -> dict:
        state = self.store.load(study_id)
        self._require_current_protocol(state)
        self._require_complete_artifacts(study_id, state)
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
                return self._dispatch(study_id, state, T.build_pass_b_task(
                    "pass-b-001", list(state.pass_a.values())))
            state.set_status("VERIFYING")
            self.store.save_manifest(study_id, state)

        if state.status == "VERIFYING":
            return self._next_verify_task(study_id, state)

        if state.status == "PASS_B_COMPLETE":
            state.set_status("VERIFYING")
            self.store.save_manifest(study_id, state)
            return self._next_verify_task(study_id, state)

        raise T.SubmissionError(f"study cannot advance from {state.status}; inspect study-status")

    @staticmethod
    def _require_current_protocol(state: StudyState) -> None:
        if (state.manifest.get("schema_version") != SCHEMA_VERSION
                or state.manifest.get("runtime_version") != RUNTIME_VERSION):
            raise T.SubmissionError(
                "legacy study protocol is read-only; run study-start to create a newly validated study")

    def _require_complete_artifacts(self, study_id, state):
        if state.status == "COMPLETE":
            missing = [name for name in ("report.json", "report.md", "motifs.json")
                       if not (self.store.study_path(study_id) / name).is_file()]
            if missing:
                raise T.SubmissionError(
                    f"completed study has missing report artifacts: {', '.join(missing)}; "
                    "restore the study backup or force-submit updated upstream analysis to regenerate reports")

    @staticmethod
    def _require_dispatched_payload(binding, task):
        if binding.get("payload_fingerprint") != response_fingerprint(task):
            raise T.SubmissionError(
                "task payload changed since dispatch; preserve the study and regenerate the affected analysis")

    def _dispatch(self, study_id: str, state: StudyState, task: dict) -> dict:
        task_type = task["task_type"]
        generation = state.manifest.get("task_generations", {}).get(task_type, 1)
        if generation > 1:
            task["task_id"] += f"-r{generation}"
        binding = {"task_type": task_type, "generation": generation,
                   "payload_fingerprint": response_fingerprint(task)}
        for field in ("batch_id", "motif_label"):
            if field in task:
                binding[field] = task[field]
        if "groups" in task:
            binding["group_ids"] = [g["group_id"] for g in task["groups"]]
        previous_binding = state.manifest["dispatched_tasks"].get(task["task_id"])
        if previous_binding is not None:
            self._require_dispatched_payload(previous_binding, task)
        state.manifest["dispatched_tasks"][task["task_id"]] = binding
        self.store.save_manifest(study_id, state)
        return task

    # ---- PASS A batching ------------------------------------------------------
    def _pending_batches(self, state: StudyState) -> list[tuple[str, list[int]]]:
        return [(batch_id, batch["group_ids"])
                for batch_id, batch in sorted(state.batches.items())
                if batch.get("status") != "SUBMITTED"]

    def _next_pass_a_task(self, study_id: str, state: StudyState) -> dict:
        pending = self._pending_batches(state)
        if not pending:
            expected = {str(g["group_id"]) for g in state.evidence["groups"]}
            if set(state.pass_a) != expected:
                raise T.SubmissionError("PASS A coverage incomplete; missing groups require a new study-start")
            state.set_status("PASS_A_COMPLETE")
            self.store.save_manifest(study_id, state)
            return self.next_task(study_id)
        batch_id, gids = pending[0]
        by_id = {g["group_id"]: g for g in state.evidence["groups"]}
        payload_groups = []
        for gid in gids:
            g = dict(by_id[gid])
            g["compare_command"] = (
                f"skillvariants compare "
                f"{state.manifest['target']['direct_skill_url']} "
                f"{g['direct_skill_url']} --json")
            payload_groups.append(g)
        task = T.build_pass_a_batch_task(f"pass-a-{batch_id.split('-')[-1]}", batch_id, payload_groups)
        state.batches[batch_id] = {"batch_id": batch_id, "group_ids": gids, "status": "DISPATCHED"}
        atomic_write_json(self.store.base / study_id / "batches.json", state.batches)
        self.store.append_event(study_id, "PASS_A_BATCH_DISPATCHED",
                                {"batch_id": batch_id, "groups": len(gids)})
        return self._dispatch(study_id, state, task)

    # ---- study-submit ----------------------------------------------------------
    @_transactional
    def submit(self, study_id: str, task_id: str, response: dict,
               force: bool = False) -> dict:
        state = self.store.load(study_id)
        self._require_current_protocol(state)
        if not isinstance(response, dict) or response.get("task_id") != task_id:
            raise T.SubmissionError("task_id mismatch between submission and response")
        binding = state.manifest.get("dispatched_tasks", {}).get(task_id)
        if binding is None:
            raise T.SubmissionError(f"task {task_id!r} was not dispatched; run study-next")
        fingerprint = __import__("hashlib").sha256(
            json.dumps(response, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        previous = state.fingerprints.get(task_id)
        if previous is not None:
            if previous == fingerprint:
                self._require_complete_artifacts(study_id, state)
                self.store.append_event(study_id, "IDEMPOTENT_RESUBMIT", {"task_id": task_id})
                return {"status": "IDEMPOTENT", "task_id": task_id}
            if not force:
                raise T.SubmissionError(
                    f"conflicting resubmission for {task_id}; use --force to override")

        if task_id.startswith("pass-a-"):
            batch_id = binding["batch_id"]
            batch_info = state.batches.get(batch_id)
            if batch_info is None:
                raise T.SubmissionError(f"unknown batch {batch_id}")
            if batch_info.get("status") == "SUBMITTED" and not force:
                raise T.SubmissionError(f"batch {batch_id} already submitted")
            task = self._rebuild_pass_a_task(batch_id, batch_info, state)
            self._require_dispatched_payload(binding, task)
            validated = T.validate_pass_a_response(task, response)
            if previous is not None:
                self._invalidate_downstream(study_id, state, "PASS_A_BATCH")
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
            if state.status not in ("PASS_A_COMPLETE", "PASS_B_READY") and not (force and previous):
                raise T.SubmissionError("PASS B submitted before PASS A completion")
            task = T.build_pass_b_task(task_id, list(state.pass_a.values()))
            self._require_dispatched_payload(binding, task)
            validated = T.validate_pass_b_response(task, response)
            if previous is not None:
                self._invalidate_downstream(study_id, state, "PASS_B_CONSOLIDATE")
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
            if state.status != "VERIFYING" and not (force and previous):
                raise T.SubmissionError("verifier task is not pending; run study-next")
            motif_label = binding.get("motif_label")
            proposed = self._find_proposed(state, motif_label)
            if proposed is None:
                raise T.SubmissionError(f"unknown motif {motif_label!r}")
            task = self._rebuild_verify_task(motif_label, proposed, state,
                                             task_id=task_id, group_ids=binding["group_ids"])
            self._require_dispatched_payload(binding, task)
            validated = T.validate_verifier_response(task, response)
            if previous is not None:
                self._invalidate_downstream(study_id, state, "VERIFY_MOTIF")
            combined = {d["group_id"]: d for d in state.verification.get(motif_label, [])}
            combined.update({d["group_id"]: d for d in validated})
            merged = [combined[gid] for gid in proposed["supporting_groups"] if gid in combined]
            self.store.save_verification(study_id, motif_label, merged)
            self.store.record_fingerprint(study_id, state, task_id, response)
            state.verification[motif_label] = merged
            self.store.append_event(study_id, "VERIFIER_SUBMITTED",
                                    {"motif": motif_label, "decisions": len(validated)})
            motifs = self._finalize_motifs(study_id, state)
            self.store.save_manifest(study_id, state)
            return {"status": "ACCEPTED", "task_id": task_id,
                    "motifs_accepted": motifs["accepted_count"],
                    "next_state": state.status}

        if task_id.startswith("final-report-"):
            if state.status != "VERIFYING" and not (force and previous):
                raise T.SubmissionError("final report requires completed verification; run study-next")
            if self._verification_pending(state):
                raise T.SubmissionError("final report blocked by pending verifier groups")
            motifs = json.loads((self.store.study_path(study_id) / "motifs.json").read_text(encoding="utf-8"))
            task = self._final_report_task(study_id, state, motifs)
            task["task_id"] = task_id
            self._require_dispatched_payload(binding, task)
            required_ok = self._validate_report(response)
            if not required_ok:
                raise T.SubmissionError(
                    "report.md missing required sections: "
                    + ", ".join(s for s in self._missing_sections(response)))
            report_json = self._report_json(state)
            notes = response.get("analyst_notes", response.get("report_md", ""))
            self.store.save_analyst_notes(study_id, notes)
            self.store.save_report_md(study_id, R.render_report_md(report_json))
            self.store.save_report_json(study_id, report_json)
            self.store.record_fingerprint(study_id, state, task_id, response)
            state.set_status("COMPLETE")
            self.store.save_manifest(study_id, state)
            self.store.append_event(study_id, "STUDY_COMPLETE", {})
            return {"status": "ACCEPTED", "task_id": task_id, "state": "COMPLETE"}

        raise T.SubmissionError(f"unknown task_id: {task_id!r}")

    # ---- verifier orchestration -------------------------------------------------
    def _cluster_precheck(self, motif: dict, state: StudyState) -> tuple[ProposedCluster, list[str]]:
        actions = []
        signature = BehaviorSignature.from_dict(motif["behavior_signature"])
        for gid in motif["supporting_groups"]:
            group = state.pass_a.get(str(gid), {})
            matching = [m for m in group.get("motifs", []) if m["change_type"] == motif["change_type"]]
            actions.append("; ".join(m["action"] for m in matching))
        proposed = ProposedCluster(
            label=motif["label"], invariant=motif["invariant"],
            signature=signature,
            member_group_ids=motif["supporting_groups"], member_actions=actions,
        )
        # 9–15 members require verification, which is satisfied by bounded tasks.
        problems = [p for p in precheck_cluster(proposed) if "mandatory verifier" not in p]
        return proposed, problems

    def _verification_pending(self, state: StudyState) -> list[tuple[str, dict, list[int]]]:
        pending = []
        index = 0
        for motif in (state.pass_b or {}).get("canonical_motifs", []):
            if len(motif["supporting_groups"]) < 3:
                continue
            index += 1
            _, problems = self._cluster_precheck(motif, state)
            if problems:
                continue  # explicit suppression before spending verifier budget
            completed = {d["group_id"] for d in state.verification.get(motif["label"], [])}
            gids = motif["supporting_groups"]
            for chunk, offset in enumerate(range(0, len(gids), MAX_VERIFIER_GROUPS_PER_TASK), 1):
                members = gids[offset:offset + MAX_VERIFIER_GROUPS_PER_TASK]
                if not set(members).issubset(completed):
                    task_id = f"verify-{index:03d}" + (f"-{chunk:03d}" if chunk > 1 else "")
                    pending.append((task_id, motif, members))
        return pending

    def _next_verify_task(self, study_id: str, state: StudyState) -> dict:
        pending = self._verification_pending(state)
        if pending:
            task_id, motif, gids = pending[0]
            return self._dispatch(study_id, state, self._rebuild_verify_task(
                motif["label"], motif, state, task_id=task_id, group_ids=gids))
        # all motifs verified -> finalize
        motifs = self._finalize_motifs(study_id, state)
        if motifs["accepted_count"] == 0:
            report = self._report_json(state)
            self.store.save_report_json(study_id, report)
            self.store.save_report_md(study_id, R.render_report_md(report))
            state.set_status("COMPLETE")
            self.store.save_manifest(study_id, state)
            self.store.append_event(study_id, "STUDY_COMPLETE_NO_MOTIFS", {})
            return {"task_type": "COMPLETE", "study_id": study_id,
                    "note": "no recurring motif passed the guardrail; see report for coverage and suppressions",
                    "report_path": str(self.store.base / study_id / "report.md")}
        return self._dispatch(study_id, state, self._final_report_task(study_id, state, motifs))

    def _find_proposed(self, state: StudyState, label: str):
        for motif in (state.pass_b or {}).get("canonical_motifs", []):
            if motif["label"] == label:
                return motif
        return None

    def _rebuild_verify_task(self, label: str, motif: dict, state: StudyState,
                             task_id: str, group_ids: list[int]) -> dict:
        by_id = {g["group_id"]: g for g in state.evidence["groups"]}
        payloads = []
        signature = BehaviorSignature.from_dict(motif["behavior_signature"])
        for gid in group_ids:
            g = dict(by_id[gid])
            matching = [m for m in state.pass_a.get(str(gid), {}).get("motifs", [])
                        if m["change_type"] == motif["change_type"]]
            if matching and all(signatures_conflict(
                    signature, BehaviorSignature.from_dict(m["behavior_signature"])) for m in matching):
                initial_actions = "; ".join(m["behavior_signature"].get("action") or ""
                                            for m in matching)
                g["verification_concern"] = (
                    "A verb-family heuristic flagged different action wording: "
                    f"initial {initial_actions!r}; canonical {signature.action!r}. "
                    "This does not prove a contradiction: synonyms can fall into different families. "
                    "Judge whether the actions describe the same behavior using both source citations; "
                    "do not decide YES or NO from the wording heuristic alone.")
            g["compare_command"] = (
                f"skillvariants compare "
                f"{state.manifest['target']['direct_skill_url']} "
                f"{g['direct_skill_url']} --json")
            payloads.append(g)
        return T.build_verify_task(task_id, motif, payloads)

    def _rebuild_pass_a_task(self, batch_id: str, batch_info: dict,
                             state: StudyState) -> dict:
        by_id = {g["group_id"]: g for g in state.evidence["groups"]}
        payload_groups = []
        for gid in batch_info["group_ids"]:
            g = dict(by_id[gid])
            g["compare_command"] = (
                f"skillvariants compare "
                f"{state.manifest['target']['direct_skill_url']} "
                f"{g['direct_skill_url']} --json")
            payload_groups.append(g)
        return T.build_pass_a_batch_task(batch_id.replace("pass-a-", "pass-a-"),
                                         batch_id, payload_groups)

    def _invalidate_downstream(self, study_id: str, state: StudyState, stage: str) -> None:
        """Invalidate dependent results only after a replacement has validated."""
        root = self.store.study_path(study_id)
        remove_types = {"FINAL_REPORT"}
        paths = [root / name for name in ("motifs.json", "report.json", "report.md", "analyst-notes.md")]
        if stage in ("PASS_A_BATCH", "PASS_B_CONSOLIDATE"):
            remove_types.add("VERIFY_MOTIF")
            paths.extend((root / "verification").glob("motif-*.json"))
            paths.append(root / "split-iterations.json")
            state.verification = {}
            state.split_iterations = {}
            state.manifest["counts"]["motifs_verified"] = 0
        if stage == "PASS_A_BATCH":
            remove_types.add("PASS_B_CONSOLIDATE")
            paths.append(root / "pass-b-proposed.json")
            state.pass_b = None
            state.manifest["counts"]["motifs_proposed"] = 0
            state.set_status("PASS_A_IN_PROGRESS")
        else:
            state.set_status("VERIFYING")
        state.manifest["counts"]["motifs_accepted"] = 0
        for path in paths:
            if not path.resolve().is_relative_to(root):
                raise ValueError("invalid artifact path outside study directory")
            path.unlink(missing_ok=True)
        dispatches = state.manifest["dispatched_tasks"]
        removed_ids = [tid for tid, task in dispatches.items() if task["task_type"] in remove_types]
        for tid in removed_ids:
            dispatches.pop(tid)
            state.fingerprints.pop(tid, None)
        generations = state.manifest.setdefault("task_generations", {})
        for task_type in remove_types:
            generations[task_type] = generations.get(task_type, 1) + 1
        self.store.save_fingerprints(study_id, state)
        self.store.save_manifest(study_id, state)
        self.store.append_event(study_id, "DEPENDENT_RESULTS_INVALIDATED", {"upstream_stage": stage})

    # ---- deterministic motif artifact --------------------------------------------
    def _finalize_motifs(self, study_id: str, state: StudyState) -> dict:
        by_id = {g["group_id"]: g for g in state.evidence["groups"]}
        accepted, suppressed = [], []
        for motif in state.pass_b["canonical_motifs"]:
            label = motif["label"]
            proposed, problems = self._cluster_precheck(motif, state)
            common = {"label": label, "proposed_group_count": len(proposed.member_group_ids),
                      "proposed_group_ids": proposed.member_group_ids,
                      "change_type": motif["change_type"], "invariant": motif["invariant"]}
            if problems:
                suppressed.append({**common,
                    "status": "SPLIT_REQUIRED" if len(proposed.member_group_ids) > 15 else "PRECHECK_FAILED",
                    "reasons": problems})
                continue
            if len(proposed.member_group_ids) < 3:
                suppressed.append({**common, "status": "NON_RECURRING",
                                   "reasons": ["fewer than three proposed groups"]})
                continue
            raw_decisions = state.verification.get(label)
            verified_ids = {d["group_id"] for d in raw_decisions or []}
            if verified_ids != set(proposed.member_group_ids):
                suppressed.append({**common, "status": "UNVERIFIED",
                                   "pending_group_ids": sorted(set(proposed.member_group_ids) - verified_ids)})
                continue
            from ..consolidation import ClusterDecision as _CD
            decisions = [
                d if isinstance(d, _CD) else _CD(
                    group_id=d["group_id"], decision=d["decision"],
                    reason=d.get("reason", ""),
                    confidence=d.get("confidence", 0.0))
                for d in raw_decisions
            ]
            repos_map = {}
            for d in decisions:
                group = by_id.get(d.group_id)
                if group:
                    repos_map[d.group_id] = group["repository"]
            result = accept_cluster(proposed, decisions, repos_map)
            entry = {
                **common,
                "display_name": motif.get("display_name", label.replace("-", " ")),
                "invariant": motif["invariant"],
                "behavior_signature": motif["behavior_signature"],
                "status": result.status,
                "rejection_rate": result.rejection_rate,
                "group_count": result.verified_yes_groups,
                "repository_count": result.verified_yes_repos,
                "supporting_groups": [
                    {"group_id": gid,
                     "evidence": next(d["evidence"] for d in raw_decisions if d["group_id"] == gid),
                     "sources": by_id[gid]["comparison"]["sources"],
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
            if set(m["supporting_groups"]) == {
                d["group_id"] for d in state.verification.get(m["label"], [])})
        state.manifest["counts"]["groups_unresolved"] = sum(
            bool(g.get("needs_source_escalation")) for g in state.pass_a.values())
        state.manifest["counts"]["groups_pending"] = max(
            0, state.manifest["counts"]["groups_total"] - len(state.pass_a))
        state.manifest["counts"]["verification_members_proposed"] = sum(
            len(m["supporting_groups"]) for m in state.pass_b["canonical_motifs"])
        state.manifest["counts"]["verification_members_resolved"] = sum(
            len(ds) for ds in state.verification.values())
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
                "Review the accepted interpretations and source coverage. Submit "
                "{\"task_id\": ..., \"analyst_notes\": \"...\"}; notes are optional and may be empty. "
                "The runtime generates report.json and report.md from validated artifacts. "
                "Your notes are stored separately as unverified prose and cannot replace counts or citations."
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
        if "analyst_notes" in response:
            T._text(response["analyst_notes"], "analyst_notes", limit=100000)
            return True
        T._text(response.get("report_md"), "report_md", required=True, limit=100000)
        return not self._missing_sections(response)

    def _report_json(self, state: StudyState) -> dict:
        motifs = json.loads((self.store.base / state.manifest["study_id"]
                             / "motifs.json").read_text(encoding="utf-8"))
        report = R.build_report_json(
            state.manifest["study_id"], state.manifest["target"],
            {**state.manifest["counts"],
             "total_groups_available": state.manifest["total_groups_available"]}, motifs,
            state.manifest.get("sampling_applied", False))
        by_id = {g["group_id"]: g for g in state.evidence["groups"]}
        covered = {(g["group_id"], m["change_type"], json.dumps(m["behavior_signature"], sort_keys=True))
                   for m in motifs["accepted"] for g in m["supporting_groups"]}
        observations = []
        for group in state.pass_a.values():
            initial = [m for m in group["motifs"] if
                       (group["group_id"], m["change_type"], json.dumps(m["behavior_signature"], sort_keys=True)) not in covered]
            if not initial or group["needs_source_escalation"]:
                continue
            source = by_id[group["group_id"]]
            observations.append({"group_id": group["group_id"], "repository": source["repository"],
                                 "direct_skill_url": source["direct_skill_url"], "motifs": initial,
                                 "verification_status": "INITIAL_UNVERIFIED_OBSERVATION",
                                 "sources": source["comparison"]["sources"]})
        report["individual_observations"] = observations
        report["unresolved_groups"] = [
            {"group_id": group["group_id"], "reason": group["escalation_reason"],
             "direct_skill_url": by_id[group["group_id"]]["direct_skill_url"]}
            for group in state.pass_a.values() if group["needs_source_escalation"]]
        report["semantic_status"] = "experimental_agent_interpretation"
        return report
