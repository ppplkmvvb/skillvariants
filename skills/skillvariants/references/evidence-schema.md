# Evidence JSON schema (`skillvariants evidence --json`)

`schema_version: "1"`. stdout carries ONLY the JSON document; progress and
warnings go to stderr. Every field below is produced by deterministic code.

## Top level

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | `"1"` | Contract version |
| `target` | object | The analyzed skill |
| `summary` | object | Deterministic counts |
| `groups` | array | One entry per mutation group (near-copy cluster) |

## target

| Field | Meaning |
|---|---|
| `repository` | `owner/repo` |
| `path` | file path inside the repo |
| `ref` | branch/tag/commit |
| `direct_skill_url` | clickable GitHub URL to the exact file |
| `name` | frontmatter `name` |
| `normalized_hash` | SHA-256 of the normalized full file (line endings/trailing whitespace unified) |

## summary

| Field | Meaning |
|---|---|
| `candidate_count` | code-search hits fetched |
| `related_variant_count` | unique variants after exact-copy collapse and relatedness gating |
| `exact_copy_count` | candidates byte-identical (after normalization) to the target |
| `mutation_group_count` | number of near-copy groups |
| `broad_archetype_counts` | group count per broad archetype |

## groups[]

| Field | Meaning |
|---|---|
| `group_id` | stable index within this run |
| `repository`, `path`, `ref` | representative file location |
| `direct_skill_url` | clickable URL to the representative SKILL.md |
| `archetype` | broad category (`compact-rewrite`, `expanded-guidance`, `routing-specialization`, `workflow-specialization`, `project-specialization`, `compatibility-wrapper`, `body-copy-with-metadata-change`, `no-label`) |
| `relatedness` | conservative relatedness score (0-1) |
| `member_count` | distinct files in the near-copy group |
| `occurrence_count` | total occurrences including duplicates |
| `structural_signals` | see below |
| `added_excerpt` / `removed_excerpt` | up to 3 short diff lines each (`\|`-joined), from the representative vs target |

## structural_signals

`length_delta` (signed ratio), `headings_added`/`headings_removed` (counts),
`commands_added`/`commands_removed` (shell-tool name lists),
`cross_skill_ref_delta` (signed count), `routing_signals` and
`wrapper_signals` (matched phrase lists), `workflow_structure_delta`
(heading-turnover share), `placeholder_signal` (template-marker density).

## Tracing chain

Every group supports: group -> representative file -> exact GitHub SKILL.md
(via `direct_skill_url`) -> comparison with the target (diff excerpts here,
full diff via `skillvariants compare <target> <variant> --json`).

## Building a compare call from evidence

For any group, construct:

```bash
skillvariants compare <target.direct_skill_url> <group.direct_skill_url> --json
```

Both URLs are always present in the payload; no URL construction by the
agent is needed or allowed.
