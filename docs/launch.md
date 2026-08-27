# Launch Copy (drafts — do not post automatically)

## Hacker News

**Title:** Show HN: SkillVariants – See how AI Agent Skills change across GitHub

**Body draft:**

I kept running into the same SKILL.md files in repo after repo. The copies
were never identical, and the interesting part turned out to be *how people
changed them*: a 280-line debugging methodology compressed into a 15-line
loop with a "stop after three failed hypotheses" rule; a design skill turned
into a five-line redirect pointing at a canonical copy; routing headers
grafted on so one skill can hand off to others.

SkillVariants is a CLI that automates that exploration: paste a public
SKILL.md URL and it searches GitHub for same-name candidates, collapses exact
and near copies into counts, gates out name-only collisions, classifies the
rest into mutation patterns (compact rewrite / expanded guidance / routing /
workflow / project specialization / compatibility wrapper), and shows up to
three representative variants per pattern with deterministic evidence.

Everything is deterministic regex + string-similarity work (RapidFuzz) — no
LLM, no embeddings, no API beyond GitHub's. Every score emits its own evidence
strings, and reruns over the same cached candidate set are byte-identical.

Validation so far: three high-copy skill families, five known adaptation
anchors (all found and correctly classified), 34 displayed representatives
reviewed by hand with zero clearly-wrong labels. That is a validation set, not
a census — search coverage and taxonomy overlap are documented limitations.

Repo: https://github.com/ppplkmvvb/skillvariants

## Reddit / developer communities

**Angle draft:**

I kept finding the same Agent Skill across many repositories, but the
interesting part was how people changed it after copying it — compressed,
wrapped as redirects, rerouted to sibling skills, specialized per project.
I built a small deterministic CLI to explore those variants from any SKILL.md
URL: it collapses the copy flood into counts, buckets what remains into
mutation patterns, and picks representative examples per pattern with
evidence you can check yourself (no LLM involved). One real finding that
hooked me: the same debugging skill exists as a 4-phase methodology, a 5-step
loop with an added stop rule, and a German translation with restructured
phases — all discoverable from one URL.

https://github.com/ppplkmvvb/skillvariants

## X / short post

Agent Skills don't just get copied — they get compressed, wrapped, rerouted,
and specialized. I built a CLI to explore those variants across GitHub:
paste a SKILL.md URL, get mutation patterns with representative diffs.
Deterministic, no LLM. https://github.com/ppplkmvvb/skillvariants

---

Notes: prefer leading with a concrete story (systematic-debugging family).
Never claim ancestry ("the original"), safety, or completeness. Attach a real
terminal screenshot/SVG when available.
