"""Persistent study session storage (spec sections 5, 13, 22).

Layout under <base>/.skillvariants/studies/<study-id>/:
  manifest.json, evidence.json, batches.json, pass-a/batch-NNN.json,
  pass-a-merged.json, pass-b-proposed.json, verification/motif-NNN.json,
  motifs.json, report.json, report.md, events.jsonl

Transitions are serialized across processes and protected by a rollback
journal. Evidence and verified source snapshots are owned by the study;
events.jsonl records committed transitions locally.
"""
from __future__ import annotations

import json
import hashlib
import re
import base64
import copy
import os
import shutil
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from filelock import FileLock, Timeout

from .models import (
    STUDIES_DIRNAME,
    SCHEMA_VERSION,
    RUNTIME_VERSION,
    DEFAULT_BATCH_SIZE,
    StudyState,
    atomic_write_json,
    read_json,
    response_fingerprint,
    study_id_for,
)


class StudyBusyError(ValueError):
    """Another process owns the study transition; retry without modifying state."""


class StudyStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base = (base_dir or Path.cwd()) / STUDIES_DIRNAME
        self._locks = {}
        self._local = threading.local()

    def study_path(self, study_id: str) -> Path:
        """Resolve a safe study directory, rejecting traversal and symlink escapes."""
        if (not isinstance(study_id, str)
                or not re.fullmatch(r"[\w-]+", study_id)
                or len(study_id) > 100):
            raise ValueError("invalid study_id: use the identifier returned by study-start")
        root = (self.base / study_id).resolve()
        if root.parent != self.base.resolve():
            raise ValueError("invalid study_id: resolved path escapes studies directory")
        return root

    @contextmanager
    def locked(self, study_id: str):
        """Cross-process, nonblocking lock also used for coherent read snapshots."""
        self.study_path(study_id)
        lock_dir = self.base / ".locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        if lock_dir.resolve().parent != self.base.resolve():
            raise ValueError("invalid lock path outside studies directory")
        lock_path = lock_dir / f"{study_id}.lock"
        if lock_path.resolve().parent != lock_dir.resolve():
            raise ValueError("invalid lock file outside studies directory")
        lock = self._locks.setdefault(study_id, FileLock(lock_path, timeout=0))
        try:
            lock.acquire(timeout=0)
        except Timeout as exc:
            raise StudyBusyError(f"study {study_id!r} is busy in another process; retry after it finishes") from exc
        try:
            yield
        finally:
            lock.release()

    @staticmethod
    def _mutable_files(root: Path) -> dict[str, Path]:
        """All mutable top-level artifacts and result files; exclude immutable evidence."""
        candidates = list(root.glob("*"))
        for directory in ("pass-a", "verification"):
            candidates.extend((root / directory).glob("*"))
        files = {}
        for path in candidates:
            if path.name in ("evidence.json", ".transaction.json"):
                continue
            if not path.resolve().is_relative_to(root):
                raise ValueError("invalid artifact path outside study directory")
            if path.is_file():
                files[path.relative_to(root).as_posix()] = path
        return files

    @staticmethod
    def _atomic_bytes(path: Path, raw: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def _recover(self, study_id: str) -> None:
        root = self.study_path(study_id)
        journal_path = root / ".transaction.json"
        if not journal_path.exists():
            return
        journal = read_json(journal_path)
        if journal.get("version") != 1 or not isinstance(journal.get("files"), dict):
            raise ValueError("invalid study recovery journal; preserve files and inspect the study")
        original = {}
        for relative, encoded in journal["files"].items():
            path = root / relative
            if (path.resolve().parent not in (root, root / "pass-a", root / "verification")
                    or path.name in ("evidence.json", ".transaction.json")):
                raise ValueError("invalid recovery journal artifact path")
            original[relative] = (path, base64.b64decode(encoded, validate=True))
        # Keep the journal until the complete prior state is back in place.
        for relative, path in self._mutable_files(root).items():
            if relative not in original:
                path.unlink()
        for path, raw in original.values():
            self._atomic_bytes(path, raw)
        journal_path.unlink()

    @contextmanager
    def transaction(self, study_id: str):
        """Rollback every artifact if a transition fails or its process is killed.

        A durable journal precedes the first mutation. Journal deletion is the
        commit point; reads recover unfinished work under the same process lock.
        """
        with self.locked(study_id):
            active = getattr(self._local, "transactions", set())
            if study_id in active:
                yield
                return
            self._recover(study_id)
            root = self.study_path(study_id)
            if not (root / "manifest.json").is_file():
                raise FileNotFoundError(f"unknown study {study_id!r}; run study-start or check --base-dir")
            files = {name: base64.b64encode(path.read_bytes()).decode("ascii")
                     for name, path in self._mutable_files(root).items()}
            journal_path = root / ".transaction.json"
            atomic_write_json(journal_path, {"version": 1, "files": files})
            self._local.transactions = active | {study_id}
            try:
                yield
            except BaseException:
                self._recover(study_id)
                raise
            else:
                journal_path.unlink()
            finally:
                self._local.transactions = active

    # ---- ids ------------------------------------------------------------
    def study_id(self, target: dict, content_hash: str, corpus_hash: str | None = None) -> str:
        return study_id_for(target, content_hash, corpus_hash)

    def exists(self, study_id: str) -> bool:
        return (self.study_path(study_id) / "manifest.json").exists()

    def find_by_target(self, target: dict, content_hash: str,
                       corpus_hash: str | None = None) -> str | None:
        """Return the study id for this exact target content hash, if any."""
        sid = self.study_id(target, content_hash, corpus_hash)
        return sid if self.exists(sid) else None

    def find_any_for_target(self, target: dict) -> str | None:
        """Any study with the same repo/path/ref (may be TARGET_CHANGED)."""
        if not self.base.exists():
            return None
        for manifest_path in sorted(self.base.glob("*/manifest.json")):
            if manifest_path.parent.name.startswith("."):
                continue
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
               sampled_group_ids: list[int], sampling_applied: bool, *,
               corpus_hash: str | None = None,
               batch_size: int = DEFAULT_BATCH_SIZE) -> tuple[str, StudyState]:
        study_id = self.study_id(target, content_hash, corpus_hash)
        with self.locked(study_id):
            return self._create_locked(target, content_hash, evidence, sampled_group_ids,
                                       sampling_applied, study_id, corpus_hash, batch_size)

    def _create_locked(self, target, content_hash, evidence, sampled_group_ids,
                       sampling_applied, study_id, corpus_hash, batch_size):
        if self.exists(study_id):
            raise FileExistsError(f"study already exists: {study_id}")
        now = self._now()
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "runtime_version": RUNTIME_VERSION,
            "study_id": study_id,
            "created_at": now,
            "updated_at": now,
            "target": {
                **target,
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
                "groups_submitted": 0,
                "groups_unresolved": 0,
                "groups_pending": len(evidence["groups"]),
                "motifs_proposed": 0,
                "motifs_verified": 0,
                "motifs_accepted": 0,
            },
            "sampling_applied": sampling_applied,
            "semantic_groups_analyzed": len(sampled_group_ids),
            "total_groups_available": evidence.get(
                "total_groups_available", len(evidence["groups"])),
            "errors": [],
            "dispatched_tasks": {},
            "task_generations": {},
            "corpus_fingerprint": corpus_hash,
            "batch_size": batch_size,
        }
        root = self.study_path(study_id)
        stage = Path(tempfile.mkdtemp(prefix=".create-", dir=self.base)).resolve()
        try:
            owned = self._own_snapshots(copy.deepcopy(evidence), stage, root)
            manifest["target"] = copy.deepcopy(owned["target"])
            manifest["target"]["normalized_hash"] = content_hash
            gids = sorted(sampled_group_ids)
            batches = {
                f"pass-a-{index:03d}": {"batch_id": f"pass-a-{index:03d}",
                    "group_ids": gids[offset:offset + batch_size], "status": "PENDING"}
                for index, offset in enumerate(range(0, len(gids), batch_size), 1)}
            for name, data in (("manifest.json", manifest), ("evidence.json", owned),
                               ("batches.json", batches), ("pass-a-merged.json", {})):
                atomic_write_json(stage / name, data)
            (stage / "pass-a").mkdir()
            (stage / "verification").mkdir()
            event = {"at": now, "event": "STUDY_CREATED", "detail": {
                "target": manifest["target"]["direct_skill_url"],
                "groups": len(gids), "sampling_applied": sampling_applied}}
            self._atomic_bytes(stage / "events.jsonl", (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8"))
            # The directory becomes visible only after every initial artifact exists.
            os.replace(stage, root)
        finally:
            if stage.exists():
                if stage.parent != self.base.resolve() or not stage.name.startswith(".create-"):
                    raise ValueError("invalid staging path outside studies directory")
                shutil.rmtree(stage)
        return study_id, self.load(study_id)

    @staticmethod
    def _own_snapshots(evidence: dict, stage: Path, root: Path) -> dict:
        """Copy only hash-verified full bytes; never reconstruct sources from excerpts."""
        def visit(value):
            if isinstance(value, list):
                for item in value:
                    visit(item)
            elif isinstance(value, dict):
                if "raw_sha256" in value:
                    digest = value["raw_sha256"]
                    original_path = value.pop("snapshot_path", None)
                    value["snapshot_available"] = False
                    value["snapshot_error"] = "Full source snapshot unavailable; use paired hunks or escalate."
                    if isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest):
                        destination = stage / "snapshots" / f"{digest}.md"
                        if destination.is_file():
                            raw = destination.read_bytes()
                        elif original_path:
                            try:
                                with Path(original_path).open("rb") as stream:
                                    raw = stream.read(5_000_001)
                            except OSError as exc:
                                value["snapshot_error"] = f"Full source snapshot unavailable: {exc}"
                                raw = None
                        else:
                            raw = None
                        if raw is not None:
                            if len(raw) > 5_000_000 or hashlib.sha256(raw).hexdigest() != digest:
                                value["snapshot_error"] = "Full source snapshot failed size/hash verification."
                            else:
                                destination.parent.mkdir(exist_ok=True)
                                destination.write_bytes(raw)
                                value["snapshot_path"] = str(root / "snapshots" / f"{digest}.md")
                                value["snapshot_available"] = True
                                value.pop("snapshot_error", None)
                for item in value.values():
                    visit(item)
        visit(evidence)
        return evidence

    def load(self, study_id: str) -> StudyState:
        with self.locked(study_id):
            if study_id not in getattr(self._local, "transactions", set()):
                self._recover(study_id)
            return self._load_locked(study_id)

    def _load_locked(self, study_id: str) -> StudyState:
        root = self.study_path(study_id)
        if not (root / "manifest.json").is_file():
            raise FileNotFoundError(
                f"unknown study {study_id!r}; run study-start or check --base-dir")
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
        atomic_write_json(self.study_path(study_id) / "manifest.json", state.manifest)

    def save_pass_a_batch(self, study_id: str, batch_id: str,
                          group_ids: list[int], response: dict) -> None:
        atomic_write_json(
            self.study_path(study_id) / "pass-a" / f"{batch_id}.json",
            {"batch_id": batch_id, "group_ids": group_ids, "response": response})

    def merge_pass_a(self, study_id: str, state: StudyState,
                     group_responses: list[dict]) -> None:
        merged = state.pass_a
        for group in group_responses:
            merged[str(group["group_id"])] = group
        atomic_write_json(self.study_path(study_id) / "pass-a-merged.json", merged)
        unresolved = sum(bool(group.get("needs_source_escalation")) for group in merged.values())
        state.manifest["counts"].update(
            groups_submitted=len(merged), groups_analyzed=len(merged) - unresolved,
            groups_unresolved=unresolved,
            groups_pending=max(0, state.manifest["counts"]["groups_total"] - len(merged)))

    def save_pass_b(self, study_id: str, response: dict) -> None:
        atomic_write_json(self.study_path(study_id) / "pass-b-proposed.json", response)

    def save_verification(self, study_id: str, motif_label: str,
                          decisions: list[dict]) -> Path:
        slug = hashlib.sha256(motif_label.encode("utf-8")).hexdigest()[:24]
        path = self.study_path(study_id) / "verification" / f"motif-{slug}.json"
        atomic_write_json(path, {
            "motif_label": motif_label, "decisions": decisions,
        })
        return path

    def save_motifs(self, study_id: str, motifs: dict) -> None:
        atomic_write_json(self.study_path(study_id) / "motifs.json", motifs)

    def save_report_json(self, study_id: str, report: dict) -> None:
        atomic_write_json(self.study_path(study_id) / "report.json", report)

    def save_report_md(self, study_id: str, content: str) -> None:
        path = self.study_path(study_id) / "report.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".md.tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)

    def save_analyst_notes(self, study_id: str, content: str) -> None:
        path = self.study_path(study_id) / "analyst-notes.md"
        if content:
            text = ("# Unverified analyst notes\n\nThis submitted prose is separate from the "
                    "engine-generated report and its counts.\n\n" + content + "\n")
            self._atomic_bytes(path, text.encode("utf-8"))
        else:
            path.unlink(missing_ok=True)

    def save_fingerprints(self, study_id: str, state: StudyState) -> None:
        atomic_write_json(self.study_path(study_id) / "fingerprints.json",
                          state.fingerprints)

    def save_split_iterations(self, study_id: str, state: StudyState) -> None:
        atomic_write_json(self.study_path(study_id) / "split-iterations.json",
                          state.split_iterations)

    def record_fingerprint(self, study_id: str, state: StudyState,
                           task_id: str, payload: dict) -> str:
        fp = response_fingerprint(payload)
        state.fingerprints[task_id] = fp
        self.save_fingerprints(study_id, state)
        return fp

    # ---- events -----------------------------------------------------------
    def append_event(self, study_id: str, event: str, detail: dict | None = None) -> None:
        path = self.study_path(study_id) / "events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"at": self._now(), "event": event, "detail": detail or {}}
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
