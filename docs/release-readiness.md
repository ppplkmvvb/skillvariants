# 0.3 release readiness

Prepared on 2026-09-10. The source changes are merged and the example site is deployed. PyPI 0.3 has not been published.

## Engineering checks

- Final frozen Windows/Python 3.13 suite: 313 tests passed.
- [PR #1](https://github.com/ppplkmvvb/skillvariants/pull/1) merged after all four [PR CI jobs](https://github.com/ppplkmvvb/skillvariants/actions/runs/34460582486) passed on Linux Python 3.11, 3.12, 3.13 and Windows Python 3.13. The [merged source CI](https://github.com/ppplkmvvb/skillvariants/actions/runs/34460889352) also passed. Every job ran the full suite, built distributions, checked provenance/export freshness and tested the installed wheel.
- Human-readable CLI assertions were verified with forced ANSI color after the first remote run exposed color-dependent failures. JSON output checks remain unmodified.
- Fault-injection tests cover process exit during Pass A, Pass B and finalization; conflicting writers are serialized.
- Runtime and source implementations received separate reviews. Findings and resolutions are retained in [runtime review](reviews/2026-09-10-runtime-review.md) and [source review](reviews/2026-09-10-source-review.md).
- Original example export is current; eight contract cases and sixteen direction cases pass corpus-integrity checks. The separate annotation exercise is described with its limitations in [evaluation.md](evaluation.md).
- Browser checks covered all three example routes, paired/full-source/unified views, copy feedback, desktop and 390px rendering. No page overflow or captured console errors were observed.
- Current documentation links resolve locally. Staged fixture/license bytes match every recorded SHA-256; upstream whitespace is intentionally preserved.
- Final local wheel, sdist and separate Skill ZIP passed build, Twine and release QA. All 20 wheel modules and 24 sdist source files matched the frozen checkout bytes.
- The wheel was installed in a separate environment with PYTHONPATH unset. Actual console commands passed local inspect, paired compare, offline study and persisted-report checks; `pip check` found no broken requirements.

Local artifact SHA-256 values (CI builds its own separately tested artifacts):

| Artifact | SHA-256 |
|---|---|
| skillvariants-0.3.0-py3-none-any.whl | `ce665d7dc2d01b0129ccad986e873e64665f8a7735c4cf39507bf23d2234011a` |
| skillvariants-0.3.0.tar.gz | `bce93d781271679e7af52fd706af288394ec1007dd2279466294d6e42a98e0f2` |
| skillvariants-skill.zip | `fa19777a2552e46864e2e7eeca6404461043d1374e62aa6daffd303eb62df4d7` |

## Actual network checks

The revised CLI fetched `obra/superpowers/skills/systematic-debugging/SKILL.md` at resolved commit `b36e0829c6d0140e93cfef2ca599b1b07d4a7797`, raw SHA-256 `808fc5717aa88ad65efff312b11c186294d3e6ee301afb584e2f86599b137787`. Opening that emitted immutable reference offline returned the same hash.

A one-page live search for this project's `name: skillvariants` completed with zero candidate occurrences after excluding the target. This checks acquisition and empty-result behavior; it is not a retrieval-recall or adoption result. Large-corpus live performance was not measured during this gate.

## Publication boundary

The reusable CI workflow verifies Linux 3.11–3.13 and Windows 3.13, builds the distributions and separate Skill ZIP, checks provenance/export freshness, and smoke-tests the installed wheel. The publishing workflow consumes those exact artifacts and requires its tag to match the package version.

The repository currently has a `github-pages` environment. The revised PyPI job names `pypi`; that environment and the matching PyPI Trusted Publisher configuration must be established before a release tag is pushed. Creating a GitHub environment alone does not register a PyPI publisher. No release tag or PyPI upload is part of this readiness record.

The [public example site](https://ppplkmvvb.github.io/skillvariants/) serves `gh-pages` revision `37c2dd044f6f36971b301f5466d06948befd00f8`, deployed after the source changes reached the default branch. GitHub Pages reported this exact revision built successfully, and the public homepage was opened in a browser and showed the new paired-source examples. Full interaction and responsive checks above were performed on the identical local web source. The revised deployment script publishes only the web tree and refuses forced ref updates.

## Remaining product evidence

Semantic analysis remains experimental. A small same-model synthetic exercise does not establish general accuracy, independent reviewer agreement or maintainer time saving. The next product validation is a real maintenance decision, as described in [ROADMAP.md](../ROADMAP.md).
