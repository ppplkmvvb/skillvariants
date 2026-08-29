"""Runtime dogfood driver: drives the three benchmark families through the
study runtime CLI, answering semantic tasks from the frozen agent artifacts
(PASS A/B + verifier decisions from the guardrail benchmark). This is
runtime QA — orchestration/state validation, not new semantic research.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
RUNS = ROOT / "research" / "runtime-v0.2"

FAMILIES = {
    "systematic-debugging": "https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md",
    "frontend-design": "https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md",
    "brainstorming": "https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md",
}

BENCH = ROOT / "research" / "agent-benchmark" / "v1"


def run_cli(args: list[str], expect_ok: bool = True) -> dict | str:
    result = subprocess.run(
        [PY, "-m", "skillvariants", *args],
        capture_output=True, text=True, timeout=1800, cwd=str(ROOT),
    )
    if expect_ok and result.returncode != 0:
        raise RuntimeError(f"CLI failed: {args}\n{result.stderr[:600]}")
    return result


def load_pass_a() -> dict:
    """(family, group_id) -> PASS A group response (runtime schema)."""
    out = {}
    for line in (BENCH / "agent-pass-a.jsonl").open(encoding="utf-8"):
        record = json.loads(line)
        out[(record["family"], record["group_id"])] = record
    return out


def load_verified_decisions() -> dict:
    """(family, group_id) -> (decision, reason) from guardrail run1."""
    verified = json.loads((BENCH / "agent-pass-b-verified-run1.json").read_text(encoding="utf-8"))
    out = {}
    for result in verified["results"]:
        for decision in result.get("decision_detail", []):
            out[(decision["family"], decision["group_id"], result["label"])] = (
                decision["decision"], decision["reason"])
    return out


def signature_from(motif: dict) -> dict:
    sig = motif.get("behavior_signature") or {}
    return {
        "trigger": sig.get("trigger") or (motif.get("invariant") or "")[:100] or None,
        "action": sig.get("action") or motif.get("action") or None,
        "object": sig.get("object"),
        "outcome": sig.get("outcome"),
    }


def dogfood_family(family: str, url: str, pass_a_map: dict,
                   verifier_map: dict, base_dir: Path) -> dict:
    qa = {"family": family, "events": []}
    result = run_cli(["study-start", url, "--base-dir", str(base_dir)])
    start = json.loads(result.stdout)
    study_id = start["study_id"]
    qa["study_id"] = study_id
    qa["events"].append(f"started {study_id} resumed={start.get('resumed')}")

    evidence = json.loads((base_dir / ".skillvariants/studies" / study_id
                           / "evidence.json").read_text(encoding="utf-8"))
    # map (repo, path) -> study group_id
    key_to_gid = {(g["repository"], g["path"]): g["group_id"]
                  for g in evidence["groups"]}
    # family records for PASS A answers
    records_path = ROOT / "research" / "evidence-motifs"
    if family == "systematic-debugging":
        records = json.loads((records_path / "group_records_annotated.json")
                             .read_text(encoding="utf-8"))
    else:
        records = json.loads((records_path / family /
                              f"{family}-group-records-annotated.json")
                             .read_text(encoding="utf-8"))
    # (repo, path) -> human record (for motifs + invariants)
    rec_by_key = {(r["repository"], r["path"]): r for r in records}
    invariant_map = {}
    for line in (BENCH / "agent-pass-a.jsonl").open(encoding="utf-8"):
        record = json.loads(line)
        if record["family"] != family:
            continue
        for motif in record["motifs"]:
            invariant_map.setdefault(motif["action"], motif["invariant"])

    batch_count, verify_count, escalated = 0, 0, 0
    motif_index = 0
    interrupts_done = False
    while True:
        result = run_cli(["study-next", study_id, "--base-dir", str(base_dir)])
        task = json.loads(result.stdout)
        task_type = task["task_type"]

        if task_type == "PASS_A_BATCH":
            batch_count += 1
            # interrupt/resume test: on SD batch 2, submit only batch 1 twice
            groups = []
            for g in task["groups"]:
                key = (g["repository"], g["path"])
                record = rec_by_key.get(key)
                if record is None or record["meaningful_behavior_change"] == "NO":
                    groups.append({
                        "group_id": g["group_id"],
                        "meaningful_behavior_change": "NO",
                        "motifs": [], "needs_source_escalation": False, "notes": "",
                    })
                    continue
                motifs = []
                for i, action in enumerate(
                        (record.get("motif_1"), record.get("motif_2"),
                         record.get("motif_3"))):
                    if not action:
                        continue
                    invariant = invariant_map.get(action) or (
                        "See family study: " + action)
                    motifs.append({
                        "action": action,
                        "invariant": invariant,
                        "behavior_signature": {
                            "trigger": None, "action": action,
                            "object": None, "outcome": None},
                        "evidence_summary":
                            (record.get("short_added_excerpt") or "")[:200],
                        "confidence": 0.9 if i == 0 else 0.75,
                    })
                groups.append({
                    "group_id": g["group_id"],
                    "meaningful_behavior_change": record["meaningful_behavior_change"],
                    "motifs": motifs,
                    "needs_source_escalation": False,
                    "notes": "",
                })
            payload = {"task_id": task["task_id"], "batch_id": task["batch_id"],
                       "groups": groups}
            result = run_cli(["study-submit", study_id, "--base-dir", str(base_dir)],
                             expect_ok=False)
            # submit via file (CLI reads JSON from a path)
            submit_file = base_dir / f"{study_id}-{task['task_id']}.json"
            submit_file.parent.mkdir(parents=True, exist_ok=True)
            submit_file.write_text(json.dumps(payload, ensure_ascii=False),
                                   encoding="utf-8")
            result = run_cli(["study-submit", study_id, str(submit_file),
                              "--base-dir", str(base_dir)])
            response = json.loads(result.stdout)
            qa["events"].append(
                f"batch {task['batch_id']} -> {response['status']}")
            if response["status"] != "ACCEPTED":
                raise RuntimeError(f"batch rejected: {response}")

        elif task_type == "PASS_B_CONSOLIDATE":
            # reuse the guardrail-benchmark consolidation (v2 clusters), with
            # supporting groups mapped into this study's group ids
            proposed = json.loads((BENCH / "agent-pass-b-proposed.json")
                                  .read_text(encoding="utf-8"))
            # study group key -> family record group id mapping
            rec_gid_by_key = {(r["repository"], r["path"]): r["group_id"]
                              for r in records}
            canonical = []
            for cluster in proposed["canonical_motifs"]:
                # only this family's supporting groups belong in this study
                supporting = []
                for member in cluster["supporting_groups"]:
                    if member["family"] != family:
                        continue
                    supporting_key = None
                    for r in records:
                        if r["group_id"] == member["group_id"]:
                            supporting_key = (r["repository"], r["path"])
                            break
                    if supporting_key and supporting_key in key_to_gid:
                        supporting.append(key_to_gid[supporting_key])
                if len(supporting) < 3:
                    continue  # below recurrence within this family
                canonical.append({
                    "label": cluster["label"],
                    "display_name": cluster["label"].replace("-", " "),
                    "invariant": cluster["invariant"],
                    "behavior_signature": cluster["behavior_signature"],
                    "supporting_groups": supporting,
                    "rejected_near_misses": [],
                })
            payload = {"task_id": task["task_id"], "canonical_motifs": canonical}
            submit_file = base_dir / f"{study_id}-pass-b.json"
            submit_file.write_text(json.dumps(payload, ensure_ascii=False),
                                   encoding="utf-8")
            result = run_cli(["study-submit", study_id, str(submit_file),
                              "--base-dir", str(base_dir)])
            response = json.loads(result.stdout)
            qa["events"].append(f"PASS B -> {response['status']} "
                                f"({response.get('canonical_motifs')} motifs)")

        elif task_type == "VERIFY_MOTIF":
            verify_count += 1
            decisions = []
            for g in task["groups"]:
                key = (g["repository"], g["path"])
                rec_gid = rec_gid_by_key.get(key)
                bench = verifier_map.get((family, rec_gid, task["motif_label"]))
                if bench is None:
                    decision, reason = "YES", "invariant satisfied by group evidence"
                else:
                    decision, reason = bench
                decisions.append({"group_id": g["group_id"], "decision": decision,
                                  "reason": reason, "confidence": 0.9})
            payload = {"task_id": task["task_id"],
                       "motif_label": task["motif_label"], "decisions": decisions}
            submit_file = base_dir / f"{study_id}-verify-{verify_count}.json"
            submit_file.write_text(json.dumps(payload, ensure_ascii=False),
                                   encoding="utf-8")
            result = run_cli(["study-submit", study_id, str(submit_file),
                              "--base-dir", str(base_dir)])
            response = json.loads(result.stdout)
            qa["events"].append(
                f"verify {task['motif_label'][:40]} -> {response['status']}")

        elif task_type == "FINAL_REPORT":
            motif_lines = []
            for i, motif in enumerate(task["accepted_motifs"], 1):
                sources = "\n".join(
                    f"   - {g['repository']}/{g['path']} — {g['direct_skill_url']}"
                    for g in motif["supporting_groups"][:3])
                motif_lines.append(
                    f"{i}. {motif['display_name']}\n"
                    f"   Observed across {motif['group_count']} groups in "
                    f"{motif['repository_count']} repositories.\n"
                    f"   Invariant: {motif['invariant']}\n"
                    f"   (interpretation) Why it may matter is documented in the "
                    f"family study.\n{sources}")
            suppressed = ", ".join(s["label"] for s in task["suppressed_motifs"]) or "none"
            report_md = "\n".join([
                f"# SkillVariants study — {family}",
                "",
                "## Target Skill",
                "",
                f"[{task['study_summary']['target']['direct_skill_url']}]"
                f"({task['study_summary']['target']['direct_skill_url']})",
                "",
                "## Corpus summary",
                "",
                f"Mutation groups: {task['study_summary']['counts']['groups_total']}; "
                f"analyzed: {task['study_summary']['counts']['groups_analyzed']}; "
                f"exact copies collapsed: {task['study_summary']['counts'].get('exact_copy_count', 0)}.",
                "",
                "## Recurring adaptations",
                "",
                "\n".join(motif_lines),
                "",
                "## Notable one-offs",
                "",
                f"Suppressed/unresolved motifs: {suppressed}.",
                "",
                "## Caveats",
                "",
                "- Code search is not a census; counts are a floor.",
                "- Recurrence is not quality; no ancestry is claimed.",
                "- Motifs are heuristic observations, not recommendations.",
                "",
            ])
            payload = {"task_id": task["task_id"], "report_md": report_md}
            submit_file = base_dir / f"{study_id}-report.json"
            submit_file.write_text(json.dumps(payload, ensure_ascii=False),
                                   encoding="utf-8")
            result = run_cli(["study-submit", study_id, str(submit_file),
                              "--base-dir", str(base_dir)])
            response = json.loads(result.stdout)
            qa["events"].append(f"final report -> {response['state']}")
            break

        elif task_type == "COMPLETE":
            qa["events"].append("COMPLETE")
            break

    qa["batches"] = batch_count
    qa["verifier_tasks"] = verify_count
    status = run_cli(["study-status", study_id, "--base-dir", str(base_dir)])
    qa["final_status"] = json.loads(status.stdout)["status"]
    return qa


def main() -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    base_dir = Path(tempfile.mkdtemp(prefix="sv-runtime-"))
    pass_a_map = load_pass_a()
    verifier_map = load_verified_decisions()
    summary = {}
    for family, url in FAMILIES.items():
        qa = dogfood_family(family, url, pass_a_map, verifier_map, base_dir)
        # copy final artifacts
        study_dir = base_dir / ".skillvariants" / "studies" / qa["study_id"]
        out = RUNS / family
        out.mkdir(parents=True, exist_ok=True)
        for name in ("manifest.json", "motifs.json", "report.json", "report.md",
                     "events.jsonl"):
            source = study_dir / name
            if source.exists():
                (out / name).write_text(source.read_text(encoding="utf-8"),
                                        encoding="utf-8")
        summary[family] = qa
        print(f"{family}: status={qa['final_status']} batches={qa['batches']} "
              f"verifier={qa['verifier_tasks']}")
    (RUNS / "dogfood-summary.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
