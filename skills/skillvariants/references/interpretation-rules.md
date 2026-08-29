# Interpretation rules

Three levels of statement. Never collapse them.

## 1. Observed fact (deterministic)

Backed by the evidence payload or the CLI. Always carries counts or hashes.

> "Observed across 6 mutation groups in 6 repositories."
> "Exact copies: 12 occurrences collapsed."
> "The representative removes 108 heading lines and adds 71."

Allowed verbs: observed, collapsed, grouped, counted, linked.

## 2. Interpretation (labeled, falsifiable)

Your reading of *why* developers made a change or what it is for. Always
introduced as interpretation:

> "This may reflect a desire to prevent implementation before explicit
> design approval."
> "This looks like an escape hatch for the failure mode where the loop
> never terminates."

Rules: never present as fact; never upgrade to "best practice";
contradictory interpretations across groups are allowed and worth showing.

## 3. User-specific suggestion (only on request)

Only when the user explicitly asks whether a pattern fits their Skill, and
only after reading their actual Skill content:

> "For your Skill, this pattern may be relevant because your current draft
> has no stop condition after failed attempts."

Rules: cite which observed motif it comes from; note the tradeoff; never
recommend merely because the pattern is recurring; never edit files in this
skill.

## Forbidden claims (hard failures)

- Ancestry: "original", "copied from", "descended from", "forked from" —
  unless real git/commit evidence exists (it almost never does here).
- Census: "all", "every", "complete ecosystem picture" — code search is
  not a census.
- Quality-by-frequency: "most popular therefore best".
- Security: any safe/unsafe judgment about a Skill.
- Fabrication: any repository, path, ref, or URL not present in the
  evidence payload.
- Silent generalization: presenting project-specific rules as if they were
  general patterns (name the project scope instead).

## Frequency wording

Correct: "Observed across 6 mutation groups in 6 repositories."
Wrong: "very common", "widely adopted", "most teams", "people always".

Recurrence threshold used by the tooling: >= 3 mutation groups, >= 3
repositories, no single repository > 50% of supporting groups. Below that,
say "observed in fewer than three independent groups" or omit.
