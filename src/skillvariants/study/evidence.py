"""Validate exact paired citations without pretending to verify their meaning."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

CHANGE_TYPES = ("ADDED", "REMOVED", "MODIFIED", "UNCHANGED")
MAX_QUOTE_LINES = 40
MAX_SNAPSHOT_BYTES = 5_000_000


def validate_paired_evidence(group: dict, evidence: dict, change_type: str) -> dict:
    """Check citations against engine-provided hunks or hash-checked snapshots.

    Full-source paths come only from the dispatched evidence, never from a
    submission. Passing this check proves quotation integrity, not that the
    proposed semantic interpretation is correct; that needs separate review.
    """
    gid = group["group_id"]
    comparison = group.get("comparison")
    if not isinstance(comparison, dict) or not isinstance(evidence, dict):
        raise ValueError(f"group {gid}: paired evidence object required")
    clean = {}
    for side in ("a", "b"):
        citation = evidence.get(side)
        source = comparison.get("sources", {}).get(side, {})
        expected_hash = source.get("raw_sha256", "")
        if not isinstance(citation, dict):
            raise ValueError(f"group {gid}: evidence.{side} citation required")
        if (not re.fullmatch(r"[a-f0-9]{64}", expected_hash)
                or citation.get("raw_sha256") != expected_hash):
            raise ValueError(f"group {gid}: evidence.{side} source hash mismatch")
        start, end = citation.get("start_line"), citation.get("end_line")
        if (type(start) is not int or type(end) is not int or start < 1
                or end < start or end - start >= MAX_QUOTE_LINES):
            raise ValueError(f"group {gid}: evidence.{side} requires a valid, bounded line range")
        hunk_id = citation.get("hunk_id")
        if hunk_id == "full-source":
            snapshot = source.get("snapshot_path")
            if not snapshot:
                raise ValueError(f"group {gid}: evidence.{side} full snapshot unavailable; escalate or abstain")
            try:
                path = Path(snapshot)
                with path.open("rb") as stream:
                    raw = stream.read(MAX_SNAPSHOT_BYTES + 1)
                if len(raw) > MAX_SNAPSHOT_BYTES:
                    raise ValueError("snapshot exceeds the evidence size limit")
                if hashlib.sha256(raw).hexdigest() != expected_hash:
                    raise ValueError("snapshot hash does not match dispatched evidence")
                lines = {i: line for i, line in enumerate(raw.decode("utf-8").splitlines(), 1)}
            except (OSError, UnicodeError, ValueError) as exc:
                raise ValueError(f"group {gid}: evidence.{side} snapshot unavailable or invalid: {exc}") from exc
        else:
            hunk = next((h for h in comparison.get("hunks", []) if h.get("hunk_id") == hunk_id), None)
            if hunk is None:
                raise ValueError(f"group {gid}: evidence.{side} unknown hunk_id")
            lines = {line["line_number"]: line["text"] for line in hunk[side]["lines"]}
        if any(i not in lines for i in range(start, end + 1)):
            raise ValueError(f"group {gid}: evidence.{side} line range is outside the source evidence")
        quote = citation.get("quote")
        actual = "\n".join(lines[i] for i in range(start, end + 1))
        if not isinstance(quote, str) or not quote.strip() or quote != actual:
            raise ValueError(f"group {gid}: evidence.{side} quote does not match exact source lines")
        clean[side] = {"hunk_id": hunk_id, "start_line": start, "end_line": end,
                       "quote": quote, "raw_sha256": expected_hash}
    if (comparison.get("truncation", {}).get("truncated")
            and any(clean[side]["hunk_id"] != "full-source" for side in ("a", "b"))):
        raise ValueError(f"group {gid}: truncated evidence requires full-source citations or source escalation")
    if change_type != "UNCHANGED":
        if comparison.get("line_text_equal") or clean["a"]["quote"] == clean["b"]["quote"]:
            raise ValueError(f"group {gid}: identical/unchanged cited text cannot establish {change_type}")
    return clean
