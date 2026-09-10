"""Run with the installed wheel's Python, with PYTHONPATH unset.

Creates an isolated temporary workspace and exercises the installed console
entry point plus an offline public StudyRuntime using original synthetic data.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile


def run_smoke(expected_version: str | None = None) -> dict:
    if os.environ.get("PYTHONPATH"):
        raise RuntimeError("Unset PYTHONPATH; this gate must verify an installed wheel")
    import skillvariants
    from skillvariants.study.runtime import StudyRuntime

    distribution = importlib.metadata.distribution("skillvariants")
    direct_url = json.loads(distribution.read_text("direct_url.json") or "{}")
    if direct_url.get("dir_info", {}).get("editable"):
        raise RuntimeError("Editable installations are not wheel smoke tests")
    installed_path = Path(skillvariants.__file__).resolve()
    source_root = Path(__file__).resolve().parents[1] / "src"
    if installed_path.is_relative_to(source_root):
        raise RuntimeError("Imported source checkout instead of installed wheel")
    if installed_path != Path(distribution.locate_file("skillvariants/__init__.py")).resolve():
        raise RuntimeError("Imported package does not match installed distribution")
    if skillvariants.__version__ != distribution.version or (expected_version and distribution.version != expected_version):
        raise RuntimeError("Installed package version does not match release metadata")
    executable = Path(sysconfig.get_path("scripts")) / ("skillvariants.exe" if os.name == "nt" else "skillvariants")
    if not executable.is_file():
        raise RuntimeError("Installed console executable is missing")

    with tempfile.TemporaryDirectory(prefix="skillvariants-wheel-") as directory:
        workspace = Path(directory)
        child_env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
        for key in ("PYTHONPATH", "GH_TOKEN", "GITHUB_TOKEN"):
            child_env.pop(key, None)

        def command(*args):
            result = subprocess.run([str(executable), *map(str, args)], cwd=workspace, env=child_env,
                                    capture_output=True, text=True, encoding="utf-8", timeout=30)
            if result.returncode:
                raise RuntimeError(f"Command {' '.join(map(str, args))} failed: {result.stderr}")
            return json.loads(result.stdout)

        text = "---\nname: package-smoke\ndescription: Original synthetic release test.\nupdated: 2026-09-10\n---\nAsk before editing.\n中文 🚀\n"
        a, b = workspace / "a.md", workspace / "b.md"
        a.write_text(text, encoding="utf-8")
        b.write_text(text.replace("Ask before editing.", "Edit without asking."), encoding="utf-8")
        inspected = command("inspect", a, "--json")
        if inspected["frontmatter"]["updated"] != "2026-09-10" or inspected["ref"]["kind"] != "local":
            raise RuntimeError("Local inspect JSON contract failed")
        compared = command("compare", a, b, "--json")
        if "-Ask before editing." not in compared["comparison"]["unified_diff"] or not compared["comparison"]["hunks"]:
            raise RuntimeError("Paired comparison evidence missing")
        identical_comparison = command("compare", a, a, "--json")["comparison"]
        target = {"repository": "synthetic/package-smoke", "path": "SKILL.md", "ref": "synthetic",
                  "direct_skill_url": "https://example.invalid/synthetic/package-smoke/SKILL.md",
                  "name": "package-smoke", "normalized_hash": hashlib.sha256(text.encode()).hexdigest()}
        evidence = {"target": target, "groups": [{"group_id": 1, "repository": "synthetic/copy",
                    "path": "SKILL.md", "ref": "synthetic", "direct_skill_url": target["direct_skill_url"],
                    "comparison": identical_comparison}]}
        runtime = StudyRuntime(base_dir=workspace, evidence_builder=lambda _: evidence)
        sid = runtime.start(target["direct_skill_url"])["study_id"]
        if command("study-status", sid, "--json")["study_id"] != sid:
            raise RuntimeError("Study status identity mismatch")
        task = command("study-next", sid, "--json")
        if task["task_type"] != "PASS_A_BATCH":
            raise RuntimeError("Offline study did not dispatch PASS A")
        response_file = workspace / "response.json"
        response_file.write_text(json.dumps({"task_id": task["task_id"], "batch_id": task["batch_id"],
                                            "groups": [{"group_id": 1, "meaningful_behavior_change": "NO",
                                                        "motifs": [], "needs_source_escalation": False}]}), encoding="utf-8")
        command("study-submit", sid, response_file, "--json")
        task = command("study-next", sid, "--json")
        if task["task_type"] != "PASS_B_CONSOLIDATE":
            raise RuntimeError("Offline study did not dispatch PASS B")
        response_file.write_text(json.dumps({"task_id": task["task_id"], "canonical_motifs": []}), encoding="utf-8")
        command("study-submit", sid, response_file, "--json")
        if command("study-next", sid, "--json")["task_type"] != "COMPLETE":
            raise RuntimeError("No-motif study failed to complete")
        report = command("study-report", sid, "--json")
        if report["study_id"] != sid:
            raise RuntimeError("Study report identity mismatch")
        study_dir = runtime.store.study_path(sid)
        if not all((study_dir / filename).is_file() for filename in ("report.json", "report.md")):
            raise RuntimeError("Completed study is missing report artifacts")
    return {"ok": True, "version": distribution.version, "installed_package": str(installed_path),
            "checks": ["local-inspect", "paired-compare", "offline-study", "persisted-reports"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-version")
    args = parser.parse_args(argv)
    try:
        result = run_smoke(args.expected_version)
    except (RuntimeError, OSError, ValueError, importlib.metadata.PackageNotFoundError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
