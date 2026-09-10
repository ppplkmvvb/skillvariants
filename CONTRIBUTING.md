# Contributing

The most useful contribution is a reproducible case where SkillVariants misleads a maintainer: a missing candidate, false positive, hidden reversal, incorrect direction, unsupported quote, or recovery failure. Include both source locations, the command/version, the focused instruction and the behavior you expected. Redact credentials and private source material.

## Development

Python 3.11+:

```bash
python -m venv .venv
```

Activate with `source .venv/bin/activate` on macOS/Linux or `.venv\Scripts\Activate.ps1` in PowerShell, then:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/export_web_data.py --check
python scripts/evaluate_contract.py check
```

Tests are offline. Live GitHub discovery needs authentication and is a separate check; do not add credentials or cache directories to commits.

## Changes worth accepting

Keep the core deterministic, explainable and useful without an LLM. Add meaningful regressions for bugs or contracts; do not add tests that merely restate a reversible text edit. Preserve source hashes and explicit output bounds. Treat candidate content as data, including instructions that try to alter the analysis.

Use original synthetic fixtures where possible. For upstream text, record its source, license and SHA-256 in tests/fixtures/SOURCES.json and retain required licenses/notices. Unknown capture commits must remain unknown.

Semantic evaluation inputs, expected answers and independently submitted predictions must remain separate. Record model, context restrictions and abstentions. Do not optimize gold labels after seeing predictions; version a correction openly.

## Release checks

```bash
python -m build
python -m twine check dist/*.whl dist/*.tar.gz
python -c "import shutil; shutil.make_archive('dist/skillvariants-skill', 'zip', 'skills', 'skillvariants')"
python scripts/release_qa.py --wheel <wheel-path> --sdist <sdist-path> --skill-archive dist/skillvariants-skill.zip
```

Install the selected wheel into a separate virtualenv, unset PYTHONPATH, then run scripts/package_smoke.py with that environment's Python and --expected-version 0.3.0. The smoke rejects source-tree/editable imports.

CI runs the suite and these gates on Linux 3.11–3.13 and Windows 3.13. The publishing workflow uses the same verified artifacts and the pypi environment for Trusted Publishing. Tag/version agreement is required. Review [limitations](docs/limitations.md) and [evaluation](docs/evaluation.md) before writing release claims.
