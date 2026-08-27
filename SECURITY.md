# Security Policy

## Reporting a vulnerability

Please report suspected vulnerabilities privately via GitHub Security
Advisories ("Report a vulnerability" on the repository's Security tab) rather
than a public issue.

Do **not** include secrets, tokens, or private repository content in issues.

## Scope notes

- Tokens are read only from the `GITHUB_TOKEN` environment variable or your
  local `gh` CLI login (`gh auth token`). They are never written to disk, to
  the cache, or into any output.
- There is no telemetry.
- Cached data under `.cache/skillvariants/` contains fetched public files and
  search results only; the directory is gitignored.
- SkillVariants analyzes text structure. It does **not** claim Skills are safe
  or unsafe, is not a security scanner, and makes no trust recommendation
  about any Skill or author.
