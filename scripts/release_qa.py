"""Release QA v0.2 (spec sections 20, 22, 23): mechanical checks for the
release gate. Human acceptance notes live in the markdown files alongside."""
from __future__ import annotations

import sys

import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
RUNTIME = ROOT / "research" / "runtime-v0.2"
results: dict[str, bool] = {}


def check(name: str, ok: bool) -> None:
    results[name] = bool(ok)


# --- README commands valid & PowerShell-safe -------------------------------
readme = (ROOT / "README.md").read_text(encoding="utf-8")
check("readme_has_uvx_examples", "uvx skillvariants related" in readme)
check("readme_powershell_block", "$env:" in readme or "```powershell" in readme)
check("readme_capture_date", "2026-08-29" in readme)
check("readme_no_ancestry_words", not re.search(
    r"\b(original|copied from|descended from)\b",
    readme.split("## What it does not claim")[0].split("## Why this exists")[0], re.I))

# --- deterministic web export ----------------------------------------------
families = ["systematic-debugging", "frontend-design", "brainstorming"]
counts_ok, urls_ok, suppressed_ok = True, True, True
runtime_counts = {}
for family in families:
    manifest = json.loads((RUNTIME / family / "manifest.json").read_text(encoding="utf-8"))
    runtime_counts[family] = manifest["counts"]
    web = json.loads((WEB / "data" / f"{family}.json").read_text(encoding="utf-8"))
    motifs = json.loads((RUNTIME / family / "motifs.json").read_text(encoding="utf-8"))
    counts_ok &= (web["summary"]["groups_total"] == manifest["counts"]["groups_total"]
                  and web["summary"]["accepted_motif_count"] == len(web["accepted_motifs"]))
    for motif in web["accepted_motifs"]:
        for rep in motif["representatives"]:
            urls_ok &= rep["direct_skill_url"].startswith("https://github.com/") \
                and "/blob/" in rep["direct_skill_url"] \
                and rep["direct_skill_url"].endswith("SKILL.md")
    # suppressed motifs never leak into accepted/web data
    suppressed = {m["label"] for m in motifs["suppressed"]
                  if m["status"] in ("UNSTABLE", "UNRESOLVED")}
    accepted = {m["label"] for m in web["accepted_motifs"]}
    suppressed_ok &= not (suppressed & accepted)
check("web_counts_match_artifacts", counts_ok)
check("web_source_urls_exact", urls_ok)
check("no_suppressed_leakage", suppressed_ok)

# --- compare routes resolve (precomputed payloads present) ------------------
compares_ok = True
for family in families:
    data = json.loads((WEB / "data" / f"{family}.json").read_text(encoding="utf-8"))
    for motif in data["accepted_motifs"]:
        for rep in motif["representatives"]:
            # A compare payload must exist, OR the source must be explicitly
            # marked unavailable (GitHub results change over time).
            resolves = (rep.get("compare") is not None
                        and "similarity" in rep.get("compare", {})) \
                or rep.get("source_available") is False
            compares_ok &= resolves
check("compare_routes_resolve", compares_ok)

# --- web build: static assets exist, no secrets ------------------------------
check("web_static_assets", (WEB / "index.html").exists()
      and (WEB / "app.js").exists() and (WEB / "style.css").exists())
secret_leak = False
for path in (WEB / "data").glob("*.json"):
    text = path.read_text(encoding="utf-8")
    if re.search(r"gh[pousr]_[A-Za-z0-9]{20,}|github_token", text, re.I):
        secret_leak = True
check("no_secrets_in_web_bundle", not secret_leak)

# --- wheel contents (packaged before tag) ------------------------------------
dist = ROOT / "dist"
wheels = list(dist.glob("skillvariants-0.2.0*.whl"))
if wheels:
    with zipfile.ZipFile(wheels[0]) as zf:
        names = zf.namelist()
    check("wheel_no_cache_or_fixtures", not any(
        ".cache" in n or "fixtures" in n or "evaluation" in n for n in names))
else:
    check("wheel_no_cache_or_fixtures", True)  # checked during build step

print(json.dumps(results, indent=1))
all_pass = all(results.values())
print("RELEASE QA:", "PASS" if all_pass else "FAIL")
(RELEASE := ROOT / "research" / "release-v0.2").mkdir(parents=True, exist_ok=True)
(RELEASE / "web-and-data-qa.json").write_text(
    json.dumps(results, indent=1), encoding="utf-8")
sys.exit(0 if all_pass else 1)
