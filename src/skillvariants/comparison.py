"""Deterministic paired differences; no inferred behavioral or absence claims."""
from __future__ import annotations

import difflib
import hashlib

from .parser import SkillDoc

EVIDENCE_POLICY = (
    "Paired snippets show local text changes, not semantic direction or global absence. "
    "When evidence is truncated or insufficient, abstain or inspect the complete source "
    "snapshots before making a claim. Repeated content does not establish independent adoption."
)


def source_identity(doc: SkillDoc) -> dict:
    """JSON-safe descriptive source metadata, including an exact raw-content hash."""
    metadata = dict(doc.source_metadata)
    metadata.setdefault("raw_sha256", hashlib.sha256(doc.raw.encode("utf-8")).hexdigest())
    if doc.source:
        metadata.setdefault("repository", doc.source.repo_slug)
        metadata.setdefault("path", doc.source.path)
        metadata.setdefault("requested_ref", doc.source.ref)
    # A parsed URL alone is not a fetched immutable snapshot.
    metadata.setdefault("immutable", False)
    metadata.setdefault("resolved_ref", None)
    return metadata


def compare_documents(a: SkillDoc, b: SkillDoc, *, max_hunks: int = 20,
                      max_lines: int = 400, max_diff_chars: int = 40000) -> dict:
    """Return raw-line paired hunks with stable ids and explicit output bounds.

    Only complete hunks are emitted. Oversized hunks are omitted and require
    full-snapshot escalation; displayed quotes are never silently shortened.
    """
    if min(max_hunks, max_lines, max_diff_chars) < 0:
        raise ValueError("Comparison bounds must be nonnegative")
    left, right = a.raw.splitlines(), b.raw.splitlines()
    matcher = difflib.SequenceMatcher(None, left, right, autojunk=False)
    hunks, omitted_hunks, omitted_lines, used_lines, used_chars = [], 0, 0, 0, 0
    for index, operations in enumerate(matcher.get_grouped_opcodes(3), start=1):
        a0, a1 = operations[0][1], operations[-1][2]
        b0, b1 = operations[0][3], operations[-1][4]
        line_count = a1 - a0 + b1 - b0
        char_count = sum(len(s) for s in left[a0:a1] + right[b0:b1])
        if (len(hunks) >= max_hunks or used_lines + line_count > max_lines
                or used_chars + char_count > max_diff_chars):
            omitted_hunks += 1
            omitted_lines += line_count
            continue
        def side(lines, start, end):
            return {"start_line": start + 1, "line_count": end - start,
                    "lines": [{"line_number": i + 1, "text": lines[i]} for i in range(start, end)]}
        hunks.append({
            "hunk_id": f"hunk-{index:03d}", "a": side(left, a0, a1), "b": side(right, b0, b1),
            "changes": [{"tag": tag, "a_start_line": i + 1, "a_line_count": j - i,
                         "b_start_line": k + 1, "b_line_count": l - k}
                        for tag, i, j, k, l in operations],
        })
        used_lines += line_count
        used_chars += char_count
    diff_chunks, diff_chars, diff_truncated = [], 0, False
    for line in difflib.unified_diff(left, right, fromfile="a/SKILL.md", tofile="b/SKILL.md", lineterm=""):
        chunk = line + "\n"
        if diff_chars + len(chunk) > max_diff_chars:
            diff_truncated = True
            break
        diff_chunks.append(chunk)
        diff_chars += len(chunk)
    sources = {"a": source_identity(a), "b": source_identity(b)}
    raw_equal = sources["a"]["raw_sha256"] == sources["b"]["raw_sha256"]
    return {
        "unified_diff": "".join(diff_chunks), "hunks": hunks,
        "sources": sources,
        "raw_equal": raw_equal, "line_text_equal": left == right,
        "formatting_changes": (["Raw source bytes differ although split line text is identical; inspect newline/encoding differences in the snapshots."]
                               if not raw_equal and left == right else []),
        "truncation": {"truncated": bool(omitted_hunks or diff_truncated),
                       "omitted_hunks": omitted_hunks, "omitted_lines": omitted_lines,
                       "unified_diff_truncated": diff_truncated, "max_hunks": max_hunks,
                       "max_lines": max_lines, "max_diff_chars": max_diff_chars},
        "evidence_policy": EVIDENCE_POLICY,
    }
