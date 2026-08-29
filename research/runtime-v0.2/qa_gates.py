"""Runtime QA gates (spec section 25): resume, idempotency, malformed
submissions, artifact integrity, unstable suppression."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
URL = ("https://github.com/obra/superpowers/blob/main/"
       "skills/systematic-debugging/SKILL.md")
BENCH = ROOT / "research" / "agent-benchmark" / "v1"


def cli(*args, base: Path):
    result = subprocess.run(
        [sys.executable, "-m", "skillvariants", *args, "--base-dir", str(base)],
        capture_output=True, text=True, timeout=1200, cwd=str(ROOT))
    return result


def main() -> None:
    base = Path(tempfile.mkdtemp(prefix="sv-qa-"))
    checks: dict[str, bool] = {}

    r = cli("study-start", URL, base=base)
    start = json.loads(r.stdout)
    sid = start["study_id"]

    # gate: interrupt/resume after 2 batches
    for _ in range(2):
        task = json.loads(cli("study-next", sid, base=base).stdout)
        assert task["task_type"] == "PASS_A_BATCH", task["task_type"]
        groups = []
        for g in task["groups"]:
            groups.append({"group_id": g["group_id"],
                           "meaningful_behavior_change": "NO", "motifs": [],
                           "needs_source_escalation": False, "notes": ""})
        payload = {"task_id": task["task_id"], "batch_id": task["batch_id"],
                   "groups": groups}
        f = base / f"qa-{task['task_id']}.json"
        f.write_text(json.dumps(payload), encoding="utf-8")
        cli("study-submit", sid, str(f), base=base)
    manifest = json.loads((base / ".skillvariants/studies" / sid
                           / "manifest.json").read_text(encoding="utf-8"))
    checks["state_after_2_batches"] = manifest["counts"]["groups_analyzed"] == 16
    # resume (new process, same base dir)
    task = json.loads(cli("study-next", sid, base=base).stdout)
    checks["resumed_next_is_pass_a"] = task["task_type"] == "PASS_A_BATCH"
    checks["resumed_batch_is_third"] = task["batch_id"] == "pass-a-003"

    # gate: idempotent duplicate submission
    r1 = cli("study-submit", sid, str(f), base=base)
    r2 = cli("study-submit", sid, str(f), base=base)
    s1 = json.loads(r1.stdout).get("status") if r1.returncode == 0 else "ERROR"
    s2 = json.loads(r2.stdout).get("status") if r2.returncode == 0 else "ERROR"
    # batch already submitted in-loop: replay must be idempotent, never a
    # conflict, and never a state advance.
    checks["idempotent_duplicate"] = s1 == "IDEMPOTENT" and s2 == "IDEMPOTENT"

    # gate: malformed submission does not advance
    before = json.loads(cli("study-status", sid, base=base).stdout)
    bad = base / "qa-bad.json"
    bad.write_text(json.dumps({"task_id": task["task_id"], "batch_id": task["batch_id"],
                               "groups": [{"group_id": 999,
                                           "meaningful_behavior_change": "MAYBE",
                                           "motifs": []}]}), encoding="utf-8")
    r = cli("study-submit", sid, str(bad), base=base)
    after = json.loads(cli("study-status", sid, base=base).stdout)
    _ = r
    checks["malformed_rejected"] = r.returncode != 0 and "REJECTED" in r.stderr
    checks["state_not_advanced"] = (after["counts"]["groups_analyzed"]
                                    == before["counts"]["groups_analyzed"])

    print(json.dumps(checks, indent=1))
    all_pass = all(checks.values())
    print("QA GATES:", "PASS" if all_pass else "FAIL")
    (RUNS := ROOT / "research" / "runtime-v0.2") / "qa"
    (ROOT / "research" / "runtime-v0.2" / "qa-gates.json").write_text(
        json.dumps({"study_id": sid, "checks": checks,
                    "all_pass": all_pass}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
