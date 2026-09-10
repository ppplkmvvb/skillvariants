# Example explorer

The static explorer contains three original approval-checkpoint examples: added, preserved and reversed. It is a reading aid with paired hunks, complete sources, a unified diff, source hashes and reproducible CLI commands. The annotations are authored interpretations, not sampled GitHub behavior.

From an installed checkout:

```bash
python scripts/export_web_data.py
python scripts/export_web_data.py --check
python -m http.server 8769 --bind 127.0.0.1 --directory web
```

Open `http://127.0.0.1:8769`. No backend, authentication, remote fonts or model service is required.

Edit the sources in `examples/approval-gate/` and the explicit example annotations in `scripts/export_web_data.py`; regenerate the export. The exporter calls the production comparison engine and rejects missing/out-of-range citations or truncated examples. CI rejects stale exports and leftover legacy study data.

Browser review on 2026-09-10 covered homepage-to-comparison navigation, complete-source and unified-diff controls, desktop rendering and a 390px mobile layout. No horizontal page overflow or captured console errors were observed.

`scripts/deploy_gh_pages.py` publishes only the web directory. It updates an existing reference with PATCH and refuses a forced branch update. Run it only for a reviewed build; tests mock remote mutations. Website availability is separate from local validation.
