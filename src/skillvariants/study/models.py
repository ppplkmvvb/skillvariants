"""Study runtime models and constants (spec sections 5-7, 23)."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA_VERSION = "2"
RUNTIME_VERSION = "0.4"

STUDIES_DIRNAME = Path(".skillvariants") / "studies"

STATUSES = (
    "CREATED", "EVIDENCE_READY", "PASS_A_IN_PROGRESS", "PASS_A_COMPLETE",
    "PASS_B_READY", "PASS_B_COMPLETE", "VERIFYING", "COMPLETE",
    "FAILED_RECOVERABLE", "FAILED_TERMINAL", "TARGET_CHANGED",
)

TASK_TYPES = ("PASS_A_BATCH", "PASS_B_CONSOLIDATE", "VERIFY_MOTIF", "FINAL_REPORT", "COMPLETE")

MEANINGFUL_VALUES = ("YES", "PARTIAL", "NO")
VERIFIER_DECISIONS = ("YES", "NO", "UNCERTAIN")

DEFAULT_BATCH_SIZE = 8
MIN_BATCH_SIZE = 4
MAX_BATCH_SIZE = 12
MAX_SEMANTIC_GROUPS = 250
MAX_VERIFIER_GROUPS_PER_TASK = 8
MAX_SPLIT_ITERATIONS = 1

REQUIRED_REPORT_SECTIONS = (
    "Target Skill", "Corpus summary", "Recurring adaptations",
    "Notable one-offs", "Caveats",
)


def atomic_write_json(path: Path, data) -> None:
    """Write JSON atomically: temp file in the same directory, then replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def study_id_for(target: dict, content_hash: str, corpus_hash: str | None = None) -> str:
    """Bind a study to source, content, and validation protocol."""
    name = (target.get("name") or target.get("path", "skill").split("/")[-1]
            .removesuffix(".md").removesuffix(".SKILL"))
    slug = "".join(ch if ch.isalnum() else "-" for ch in name.lower())[:40].strip("-")
    identity = {
        "source": {key: target.get(key) for key in (
            "repository", "path", "ref", "direct_skill_url", "resolved_ref", "raw_sha256")},
        "content_hash": content_hash,
        "corpus_fingerprint": corpus_hash,
        "schema_version": SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
    }
    digest = response_fingerprint(identity)[:16]
    return f"{slug or 'skill'}-{digest}"


def response_fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def source_fingerprint_fields(source: dict) -> dict:
    """Source/content identity without fetch time, local paths or cache state."""
    fields = ("kind", "repository", "path", "ref", "requested_ref", "resolved_ref",
              "direct_skill_url", "raw_sha256", "normalized_hash", "blob_sha")
    stable = {key: source[key] for key in fields if key in source}
    if isinstance(source.get("source"), dict):
        stable["source"] = source_fingerprint_fields(source["source"])
    return stable


def group_fingerprint_fields(group: dict) -> dict:
    stable = source_fingerprint_fields(group)
    stable["occurrence_count"] = group.get("occurrence_count", 1)
    stable["occurrences"] = sorted(
        (source_fingerprint_fields(item) for item in group.get("occurrences", [])),
        key=response_fingerprint)
    stable["comparison_sources"] = {
        side: source_fingerprint_fields(source)
        for side, source in group.get("comparison", {}).get("sources", {}).items()}
    return stable


def corpus_fingerprint(evidence: dict, selected_groups: list[dict]) -> str:
    """Identity of the actual captured corpus and selected semantic scope."""
    return response_fingerprint({
        "target": source_fingerprint_fields(evidence["target"]),
        "groups": sorted((group_fingerprint_fields(g) for g in evidence["groups"]), key=response_fingerprint),
        "selected_groups": sorted((group_fingerprint_fields(g) for g in selected_groups), key=response_fingerprint),
        "schema_version": SCHEMA_VERSION, "runtime_version": RUNTIME_VERSION,
    })


@dataclass
class StudyState:
    """In-memory view of manifest.json plus derived orchestration state."""

    manifest: dict
    evidence: dict
    batches: dict  # batch_id -> {"group_ids": [...], "status": "..."}
    pass_a: dict  # group_id -> pass-a group response
    pass_b: dict | None  # proposed canonical motifs
    verification: dict  # motif_label -> list of decisions
    fingerprints: dict  # task_id -> response fingerprint (idempotency)
    split_iterations: dict  # motif_label -> int

    @property
    def status(self) -> str:
        return self.manifest["status"]

    def set_status(self, status: str) -> None:
        if status not in STATUSES:
            raise ValueError(f"invalid study status: {status!r}")
        self.manifest["status"] = status
