# Mutation Archetypes

> Archetypes are heuristic descriptive categories, not a formal taxonomy and
> not provenance claims. A variant can legitimately match more than one; the
> tool designates one `primary_mutation_type` deterministically and keeps the
> others as secondary labels with their evidence.

## Compact rewrite

**Meaning:** the same Skill purpose, deliberately reduced — a methodology
turned into a checklist.

**Deterministic signals:**

- same/strongly-related skill name, gated by content corroboration
- large negative length delta (measured with a symmetric log-ratio so ×2 and
  ÷2 count equally)
- body similarity above a floor (it is a rewrite of *this* skill, not a new one)
- not a wrapper

**Representative shape:**

```text
Archive228/loopkit
  relatedness: 0.54
  length changed by -85%
  17 headings added/removed
```

**Known ambiguity:** deletion-only truncations also shrink; they are penalized
(but not excluded) when nothing new is added. Very faithful paraphrases can
score near the `workflow-specialization` boundary.

## Expanded guidance

**Meaning:** the original plus meaningful additions — examples, checklists,
environment-specific rules.

**Signals:** positive length delta, added headings, added commands;
a coherence term (raw text ratio) plus a multiplicative penalty keep giant
absorber files that merely *contain* the target from winning this section.
Placeholder-dense files are additionally down-ranked.

**Known ambiguity:** absorbers with moderate coherence can still slip through;
"expanded" can be indistinguishable from "re-authored with additions".

## Routing specialization

**Meaning:** keeps the original workflow but adds boundaries between sibling
skills.

**Signals:** routing-boundary headings/phrases ("Routing Boundary", "do not
use", "owns", "route to"), growth in cross-skill references. File size has
little weight here.

**Known ambiguity:** packaging catalogs add boilerplate routing headers to
unmodified copies; those appear here rather than under exact copies.

## Workflow specialization

**Meaning:** phases/process restructured for a different environment or tool
(added planning gates, approval flows, execution loops).

**Signals:** heading turnover (added+removed section names), planning/approval
language, environment-process terms, same-name match.

**Known ambiguity:** overlaps intentionally with project specialization —
project-specific processes look like workflow changes. The primary label is
deterministic; secondary labels carry the rest. Refinement is backlog item #1.

## Project specialization

**Meaning:** adapted to one repository/product: project paths, migration
notes, product names, house rules.

**Signals:** explicit project vocabulary ("this project/repository",
"migration note(s)", "legacy", tool-specific modes), frontmatter key changes.
Used conservatively; never as a fallback for "different text".

**Known ambiguity:** this is the label most often absorbed by workflow
specialization in practice.

## Compatibility wrapper

**Meaning:** a tiny document whose job is redirecting to a canonical copy.

**Signals:** canonical pointer in frontmatter (`canonical_skill` etc.),
resolve/wrapper language, very short body. Body similarity is *not* required —
a five-line redirect is a valid and useful mutation story.

**Known ambiguity:** documentation pages that merely mention a canonical path
can resemble wrappers if they are short.

## Copy metadata (not archetype sections)

`exact-copy` and `body-copy-with-metadata-change` are reported as counts and
labels, never as story sections: hundreds of identical files would bury every
other mutation pattern.
