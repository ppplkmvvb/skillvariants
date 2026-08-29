"""Persistent study session storage (spec sections 5, 13, 22).

Layout under <base>/.skillvariants/studies/<study-id>/:
  manifest.json, evidence.json, batches.json, pass-a/batch-NNN.json,
  pass-a-merged.json, pass-b-proposed.json, verification/motif-NNN.json,
  motifs.json, report.json, report.md, events.jsonl

All JSON writes are atomic. events.jsonl is append-only, local-only.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import (
    STUDIES_DIRNAME,
    StudyState,
    atomic_write_json,
    read_json,
    response_fingerprint,
    study_id_for,
)


class StudyStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base = (base_dir or Path.cwd()) / STUDIES_DIRNAME

    # ---- ids ------------------------------------------------------------
    def study_id(self, target: dict, content_hash: str) -> str:
        return study_id_for(target, content_hash)

    def exists(self, study_id: str) -> bool:
        return (self.base / study_id / "manifest.json").exists()

    def find_by_target(self, target: dict, content_hash: str) -> str | None:
        """Return the study id for this exact target content hash, if any."""
        sid = self.study_id(target, content_hash)
        return sid if self.exists(sid) else None

    def find_any_for_target(self, target: dict) -> str | None:
        """Any study with the same repo/path/ref (may be TARGET_CHANGED)."""
        if not self.base.exists():
            return None
        for manifest_path in sorted(self.base.glob("*/manifest.json")):
            try:
                m = read_json(manifest_path)
            except (json.JSONDecodeError, OSError):
                continue
            t = m.get("target", {})
            if (t.get("repository") == target.get("repository")
                    and t.get("path") == target.get("path")
                    and t.get("ref") == target.get("ref")):
                return manifest_path.parent.name
        return None

    # ---- creation / loading ---------------------------------------------
    def create(self, target: dict, content_hash: str, evidence: dict,
               sampled_group_ids: list[int], sampling_applied: bool) -> tuple[str, StudyState]:
        study_id = self.study_id(target, content_hash)
        if self.exists(study_id):
            raise FileExistsError(f"study already exists: {study_id}")
        now = self._now()
        manifest = {
            "schema_version": "1",
            "runtime_version": "0.2",
            "study_id": study_id,
            "created_at": now,
            "updated_at": now,
            "target": {
                "repository": target["repository"],
                "path": target["path"],
                "ref": target["ref"],
                "direct_skill_url": target["direct_skill_url"],
                "name": target.get("name"),
                "normalized_hash": content_hash,
            },
            "status": "EVIDENCE_READY",
            "counts": {
                "groups_total": len(evidence["groups"]),
                "groups_analyzed": 0,
                "motifs_proposed": 0,
                "motifs_verified": 0,
                "motifs_accepted": 0,
            },
            "sampling_applied": sampling_applied,
            "semantic_groups_analyzed": len(sampled_group_ids),
            "total_groups_available": evidence.get(
                "total_groups_available", len(evidence["groups"])),
            "errors": [],
        }
        (self.base / study_id).mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.base / study_id / "manifest.json", manifest)
        atomic_write_json(self.base / study_id / "evidence.json", evidence)
        atomic_write_json(self.base / study_id / "batches.json", {})
        atomic_write_json(self.base / study_id / "pass-a-merged.json", {})
        (self.base / study_id / "pass-a").mkdir(parents=True, exist_ok=True)
        (self.base / study_id / "verification").mkdir(parents=True, exist_ok=True)
        state = self.load(study_id)
        self.append_event(study_id, "STUDY_CREATED", {
            "target": manifest["target"]["direct_skill_url"],
            "groups": manifest["counts"]["groups_total"],
            "sampling_applied": sampling_applied,
        })
        return study_id, state

    def load(self, study_id: str) -> StudyState:
        root = self.base / study_id
        manifest = read_json(root / "manifest.json")
        evidence = read_json(root / "evidence.json")
        batches = read_json(root / "batches.json")
        pass_a = read_json(root / "pass-a-merged.json")
        pass_b_path = root / "pass-b-proposed.json"
        pass_b = read_json(pass_b_path) if pass_b_path.exists() else None
        verification = self._load_verification(root)
        fingerprints = read_json(root / "fingerprints.json") if (
                root / "fingerprints.json").exists() else {}
        splits_path = root / "split-iterations.json"
        splits = read_json(splits_path) if splits_path.exists() else {}
        return StudyState(
            manifest=manifest, evidence=evidence, batches=batches,
            pass_a=pass_a, pass_b=pass_b, verification=verification,
            fingerprints=fingerprints, split_iterations=splits,
        )

    @staticmethod
    def _load_verification(root: Path) -> dict:
        verification: dict[str, list] = {}
        vdir = root / "verification"
        if vdir.exists():
            for path in sorted(vdir.glob("motif-*.json")):
                data = read_json(path)
                verification[data["motif_label"]] = data["decisions"]
        return verification

    # ---- persistence ------------------------------------------------------
    def save_manifest(self, study_id: str, state: StudyState) -> None:
        state.manifest["updated_at"] = self._now()
        atomic_write_json(self.base / study_id / "manifest.json", state.manifest)

    def save_pass_a_batch(self, study_id: str, batch_id: str,
                          group_ids: list[int], response: dict) -> None:
        atomic_write_json(
            self.base / study_id / "pass-a" / f"{batch_id}.json",
            {"batch_id": batch_id, "group_ids": group_ids, "response": response})

    def merge_pass_a(self, study_id: str, state: StudyState,
                     group_responses: list[dict]) -> None:
        merged = state.pass_a
        for group in group_responses:
            merged[str(group["group_id"])] = group
        atomic_write_json(self.base / study_id / "pass-a-merged.json", merged)
        state.manifest["counts"]["groups_analyzed"] = len(merged)

    def save_pass_b(self, study_id: str, response: dict) -> None:
        atomic_write_json(self.base / study_id / "pass-b-proposed.json", response)

    def save_verification(self, study_id: str, motif_label: str,
                          decisions: list[dict]) -> Path:
        slug = motif_label.replace("/", "-")[:80]
        path = self.base / study_id / "verification" / f"motif-{slug}.json"
        atomic_write_json(path, {
            "motif_label": motif_label, "decisions": decisions,
        })
        return path

    def save_motifs(self, study_id: str, motifs: dict) -> None:
        atomic_write_json(self.base / study_id / "motifs.json", motifs)

    def save_report_json(self, study_id: str, report: dict) -> None:
        atomic_write_json(self.base / study_id / "report.json", report)

    def save_report_md(self, study_id: str, content: str) -> None:
        path = self.base / study_id / "report.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".md.tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)

    def save_fingerprints(self, study_id: str, state: StudyState) -> None:
        atomic_write_json(self.base / study_id / "fingerprints.json",
                          state.fingerprints)

    def save_split_iterations(self, study_id: str, state: StudyState) -> None:
        atomic_write_json(self.base / study_id / "split-iterations.json",
                          state.split_iterations)

    def record_fingerprint(self, study_id: str, state: StudyState,
                           task_id: str, payload: dict) -> str:
        fp = response_fingerprint(payload)
        state.fingerprints[task_id] = fp
        self.save_fingerprints(study_id, state)
        return fp

    # ---- events -----------------------------------------------------------
    def append_event(self, study_id: str, event: str, detail: dict | None = None) -> None:
        path = self.base / study_id / "events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"at": self._now(), "event": event, "detail": detail or {}}
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
