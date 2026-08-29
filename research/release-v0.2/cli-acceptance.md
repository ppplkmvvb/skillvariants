# CLI Acceptance — v0.2.0

Run from a clean environment via `uvx` (published package) and locally via
the repository (development). Windows PowerShell examples checked for
syntax safety (backtick line continuation, `$env:` variable form).

## Commands

| Command | Result |
|---|---|
| `uvx skillvariants --help` | PASS — usage + all commands listed |
| `uvx skillvariants inspect <URL>` | PASS — frontmatter/body/signals rendered |
| `uvx skillvariants related <URL>` | PASS — archetype map (mutations mode default) |
| `uvx skillvariants related <URL> --mode closest` | PASS — similarity order |
| `uvx skillvariants evidence <URL> --json` | PASS — schema v1, clean stdout |
| `uvx skillvariants compare <A> <B> --json` | PASS — similarity + mutation + diff |
| `uvx skillvariants study-start/status/next/submit/report` | PASS — runtime loop |

## JSON contracts

- `evidence --json`, `related --json`, `compare --json`,
  `study-report --json` all parse via `json.loads`.
- Hash fields are 64-char hex digests; no normalized source text leaks.
- stdout carries only JSON; warnings/errors go to stderr.

## Notes

- Before the PyPI 0.2.0 upload, `uvx` acceptance used
  `uvx --from git+https://github.com/ppplkmvvb/skillvariants.git skillvariants ...`
  (the published 0.1.1 lacks the study runtime); after publish, the plain
  `uvx skillvariants` path was re-verified.
- Without authentication the CLI exits with the short actionable message
  ("Set GITHUB_TOKEN or authenticate with `gh auth login`").
