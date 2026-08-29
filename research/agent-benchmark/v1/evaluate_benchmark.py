"""Benchmark evaluation: A/B/C/D metrics (spec section 11)."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
manifest = json.loads((BASE / "benchmark-manifest.json").read_text(encoding="utf-8"))
pass_a = [json.loads(line) for line in (BASE / "agent-pass-a.jsonl").open(encoding="utf-8")]
pass_b = json.loads((BASE / "agent-pass-b.json").read_text(encoding="utf-8"))

human_groups = {(g["family"], g["group_id"]): g for g in manifest["groups"]}

# ---------- A. Meaningful-change agreement ----------
confusion = Counter()
exact = 0
for record in pass_a:
    key = (record["family"], record["group_id"])
    human = human_groups[key]["human_meaningful"]
    agent = record["meaningful_behavior_change"]
    confusion[(human, agent)] += 1
    if human == agent:
        exact += 1
macro = exact / len(pass_a)
print("=== A. Meaningful-change agreement ===")
print(f"exact agreement: {exact}/{len(pass_a)} = {macro:.1%}  (target >= 80%)")
print("confusion (human -> agent):")
for (h, a), n in sorted(confusion.items(), key=lambda kv: -kv[1]):
    print(f"  {h:8s} -> {a:8s}: {n}")

# ---------- B. Motif semantic coverage ----------
# Strong human canonical = recurring (>=3 groups) + majority worth=YES.
strong_human = []
for m in manifest["canonical_motifs"]:
    if m["group_count"] < 3:
        continue
    worths = Counter(
        human_groups[(m["family"], gid)]["human_worth_reviewing"]
        for gid in m["supporting_groups"]
    )
    if worths.get("YES", 0) > len(m["supporting_groups"]) / 2:
        strong_human.append(m)
print(f"\n=== B. Motif semantic coverage ===")
print(f"strong human canonical motifs: {len(strong_human)}")
for m in strong_human:
    print(f"  [{m['family']}] {m['label']}  groups={m['group_count']}")
# Agent recurring canonical labels (for manual MATCH mapping)
agent_recurring = [c for c in pass_b["canonical_motifs"]
                   if len(c["supporting_groups"]) >= 3]
print(f"agent recurring canonical motifs: {len(agent_recurring)}")

# ---------- C. Over-merge audit (structural; sample below) ----------
print(f"\n=== C. Over-merge audit candidates ===")
for c in agent_recurring:
    print(f"  {c['label'][:56]:56s} groups={len(c['supporting_groups'])}")

# ---------- D. Evidence faithfulness sample ----------
import random
random.seed(42)
claims = []
for record in pass_a:
    for m in record["motifs"]:
        claims.append((record["family"], record["group_id"], m))
sample = random.sample(claims, min(30, len(claims)))
faithful = 0
for family, gid, m in sample:
    key = (family, gid)
    human = human_groups[key]
    ev = m["evidence"][0]["summary"] if m["evidence"] else ""
    supported = bool(ev) and (
        ev[:60] in (human.get("added_excerpt", "") + human.get("removed_excerpt", ""))
        or len(ev) < 10)
    faithful += supported
print(f"\n=== D. Evidence faithfulness (sampled {len(sample)}) ===")
print(f"supported: {faithful}/{len(sample)} = {faithful/len(sample):.0%}  (target >= 95%)")
