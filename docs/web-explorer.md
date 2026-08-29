# Web Explorer

A static, precomputed-data explorer over the three validated studies:
`systematic-debugging`, `frontend-design`, `brainstorming`.

## Data flow

```text
research/runtime-v0.2/<family>/{manifest,motifs}.json
  ↓  scripts/export_web_data.py (deterministic)
web/data/<family>.json
  ↓  web/index.html + app.js (hash routing, no build step)
home → study → motif → compare
```

- Counts, invariants, behavior signatures, and source URLs come from the
  runtime artifacts — never hand-entered in UI code.
- Interpretation/tradeoff text comes from the frozen family studies and is
  labeled as interpretation.
- Compare payloads (target vs representative: similarity, length change,
  mutation, brief diff) are precomputed with the deterministic compare
  pipeline at export time.

## Constraints

Static frontend only: no backend, no database, no auth, no secrets, no
hosted LLM calls, no live arbitrary-URL analysis. Deployable to GitHub
Pages or any static host.

## Wording rules

Never shown: "best practice", "recommended", "widely adopted",
"independently invented", recommendation scores, or "best variant".
Shown: observed facts (counts + sources), interpretation (labeled), and
tradeoffs (labeled).
