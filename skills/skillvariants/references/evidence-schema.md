# Evidence schema 2

stdout contains JSON; progress/errors use stderr. Read task-specific instructions returned by the installed runtime. This schema is incompatible with legacy semantic submissions.

## Evidence envelope

target contains repository, path, ref, direct_skill_url, name, normalized_hash and source metadata. A fetched source includes requested/resolved refs, raw_sha256, capture/cache information and snapshot_path when available.

summary distinguishes candidate_count (unique repository/path hits excluding target), fetched_count, fetch_error_count, unique_variant_count (before gating), related_variant_count (after gating), exact_copy_count (normalized target-matching occurrences), mutation_group_count and related_occurrence_count. Consult the payload's count_definitions.

groups contains one distinct normalized candidate per entry. group_id is local to this corpus. Each includes its representative URL, normalized_hash, occurrences, comparison, structural_signals, and short display excerpts. member_count is 1; occurrence_count includes duplicate locations. These are not independent adoption counts.

## comparison

- sources.a and sources.b: source identity and raw SHA-256.
- hunks: stable hunk_id plus separate a/b start_line, line_count and lines arrays.
- Each raw source line is {line_number, text}. Frontmatter participates in line numbering.
- changes records tagged equal/insert/delete/replace ranges.
- unified_diff: bounded full diff text.
- raw_equal, line_text_equal, formatting_changes: byte/line distinctions.
- truncation: explicit flag and omitted-hunk/line/output bounds.

added_excerpt and removed_excerpt are display summaries. They cannot replace comparison evidence.

## Citation

```json
{
  "hunk_id": "hunk-001",
  "start_line": 9,
  "end_line": 9,
  "quote": "3. Do not implement before the user approves the plan.",
  "raw_sha256": "<copy the exact 64-character hash from sources.a>"
}
```

Every semantic motif needs evidence.a and evidence.b, each with its own valid citation. Ranges are inclusive, at most 40 lines, joined with newline in quote. Use change_type ADDED/REMOVED/MODIFIED/UNCHANGED.

When comparison.truncation.truncated is true, use hunk_id=full-source for BOTH sides after reading the supplied snapshot files. The runtime verifies file hashes and exact quotes. Missing or insufficient sources require escalation with no motifs. A negative finding over truncated evidence requires equivalent paired review_evidence.

Exact quote validation proves the cited text is present. It does not prove global absence, behavioral equivalence or semantic entailment.

## Final task

Submit {"task_id":"<exact dispatched id>","analyst_notes":""}. Optional notes are stored separately. The runtime renders report.md from validated report.json with paired citations and deterministic counts.
