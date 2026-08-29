# Launch drafts — v0.2 (do not post automatically)

## GitHub release draft

**Title:** SkillVariants v0.2.0 — Agent Study Runtime + Web Explorer

**Body:**

SkillVariants can now power an end-to-end Agent study of how a public Agent
Skill has been adapted across GitHub.

**What's new**

- **Agent Study Runtime** — persistent, resumable study sessions
  (`study-start` / `study-next` / `study-submit` / `study-report`) with
  validated submissions, idempotent replays, and deterministic recurrence
- **Installable Agent Skill** — copy `skills/skillvariants/` into your
  agent's skills directory; the agent drives the whole study
- **Agent-facing evidence JSON** — `skillvariants evidence <url> --json`
- **Semantic consolidation guardrail** — behavior signatures, strict
  invariants, independent verifier, deterministic acceptance (over-merge
  0% in the guarded benchmark)
- **Recurring adaptation reports** — accepted motifs with real source
  implementations
- **Web explorer** — static, precomputed studies for three families
- **CLI UX** — cleaner help/errors, PowerShell-safe examples

**How to try**

```bash
uvx skillvariants related   https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md
```

Or install the Agent Skill and ask your agent to study any public SKILL.md
URL. Requires Python 3.11+ and GitHub auth (`GITHUB_TOKEN` / `gh auth login`).

**Limitations** — code search is not a census; results change over time;
recurrence is not quality; no ancestry is claimed. See docs/limitations.md.

## Hacker News

**Title:** Show HN: SkillVariants – your coding agent studies how Agent Skills evolve on GitHub

**Body:**

I kept finding the same Agent Skill in repo after repo, but the interesting
part was what people changed: a 280-line debugging methodology compressed
into a 15-line loop with a "stop after 3 failed fixes" rule; a design skill
reduced to a redirect pointing at a canonical copy; routing headers grafted
on so skills can hand work to each other.

SkillVariants is a deterministic CLI + Agent Skill. Paste a public SKILL.md
URL and it searches GitHub for same-name candidates, collapses exact and
near copies into counts, classifies the rest into mutation patterns, and -
new in v0.2 - runs a resumable study runtime: the agent analyzes each group,
consolidates motifs only under strict behavior-equivalence invariants, and
an independent verifier re-checks every member before the tool computes
recurrence. No hosted LLM; the engine never invents counts or URLs.

Validation: three skill families, 243 human-audited mutation groups, five
known adaptation anchors (all found and correctly classified), and a
guardrail that cut semantic over-merges from 26% to 0%. Code search is not a
census and no ancestry is claimed - limitations are documented.

Repo: https://github.com/ppplkmvvb/skillvariants

## Reddit draft

I kept finding the same Agent Skill across many repositories - but the
interesting part was how people changed it after copying it: compressed into
checklists, wrapped as redirects, rerouted to sibling skills, specialized
per project. v0.2 of my little tool runs the whole study from one prompt: it
collapses the copy flood into counts, clusters what remains into recurring
adaptation motifs (with a guardrail so clusters only survive when every
member really implements the same behavior), and shows real source
implementations. Deterministic engine, your own agent does the reasoning,
nothing hosted.

One concrete finding: the same debugging skill exists as a 4-phase
methodology, a 5-step loop with an added stop rule, and a German translation
with restructured phases - all discoverable from one URL.

https://github.com/ppplkmvvb/skillvariants

## X / LinkedIn short draft

Agent Skills get copied and adapted across GitHub, but it is hard to see
what actually changed. SkillVariants turns those variants into recurring
adaptations with real source implementations - driven by your coding agent,
counted deterministically. https://github.com/ppplkmvvb/skillvariants

## Demo asset checklist

- [x] Real terminal SVG of `related --mode mutations`
      (docs/assets/skillsvariants-related-demo.svg)
- [ ] Agent conversation demo (screen recording; capture before launch)
- [ ] Web explorer screenshot (home + motif detail)

## Links

- GitHub: https://github.com/ppplkmvvb/skillvariants
- PyPI: https://pypi.org/project/skillvariants/
- Web: (GitHub Pages URL after deploy)
- v0.1.1 release: https://github.com/ppplkmvvb/skillvariants/releases/tag/v0.1.1
