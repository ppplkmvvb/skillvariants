"""PASS A annotation: write human motif coding into the worksheet.

Coding was performed group-by-group from research/evidence-motifs/
review_bundle.txt BEFORE any frequency aggregation (spec section 11).
"""
from __future__ import annotations

import csv
import json
from collections import Counter

from pathlib import Path

OUT = Path(__file__).resolve().parent

# gid: (meaningful_behavior_change, worth_reviewing, [motif labels])
CODING = {
    1: ("NO", "NO", []),
    2: ("YES", "YES", ["Require announcing activation before debugging",
                      "Route completion verification to a separate verification Skill"]),
    3: ("YES", "YES", ["Add concrete numbered sub-steps inside each phase",
                      "Add project-specific debugging commands"]),
    4: ("PARTIAL", "MAYBE", ["Split debugging into reproduce/isolate phases with quantitative rate"]),
    5: ("YES", "YES", ["Rewrite methodology as hypothesis-driven data-flow-traced process",
                      "Add violation-indicator red flags"]),
    6: ("NO", "NO", []),
    7: ("PARTIAL", "MAYBE", ["Compact four-phase structure with sparse section removal"]),
    8: ("YES", "YES", ["Add explicit routing boundary: do not use outside debugging"]),
    9: ("NO", "NO", []),
    10: ("YES", "MAYBE", ["Restructure to red-flags-stop process with mandatory phase ordering"]),
    11: ("PARTIAL", "YES", ["Route failing-test writing to TDD skill and verification to separate skill"]),
    12: ("YES", "PARTIAL", ["Swap superpowers:-style skill references to unqualified local references"]),
    13: ("NO", "NO", []),
    14: ("YES", "MAYBE", ["Add trigger-context to iron-law phrasing"]),
    15: ("YES", "YES", ["Add repo-local nix purity rule and route to related skills"]),
    16: ("PARTIAL", "YES", ["Explicitly cite lineage as Lifted-from-superpowers and slim"]),
    17: ("YES", "YES", ["Add dedicated Related Skills heading with 6 cross-skill refs"]),
    18: ("NO", "NO", []),
    19: ("YES", "YES", ["Add escalation rule after 3+ failed fixes", "Add red flags returning to Phase 1"]),
    20: ("YES", "YES", ["Add The Feedback Loop Rule heading"]),
    21: ("YES", "MAYBE", ["Rename phases to Hypothesis Formation / Minimal Fix / Verification"]),
    22: ("YES", "YES", ["Add Feedback Loop Rule and example-driven guidance (expanded)"]),
    23: ("YES", "PARTIAL", ["Add expanded ESPECIALLY-when guidance + python tooling"]),
    24: ("YES", "PARTIAL", ["Add explicit per-command debugging guidance (npx/pipx)"]),
    25: ("YES", "YES", ["Add mandatory-phase-order enforcement marker", "Add 3+ fixes fail escalation handler"]),
    26: ("YES", "YES", ["Add slash-command usage wrapper", "Add bail-out check before Phase 1"]),
    27: ("NO", "NO", []),
    28: ("YES", "PARTIAL", ["Add Related Skills heading with cross-skill route"]),
    29: ("YES", "PARTIAL", ["Add explicit Purpose section with goals"]),
    30: ("YES", "YES", ["Replace four phases with observed workflow + Hard Gates + output contract"]),
    31: ("YES", "YES", ["Add The 3-failures rule plus red-flag return to Phase 1"]),
    32: ("YES", "YES", ["Restructure around capture symptom / build feedback loop / reproduce or bound"]),
    33: ("YES", "YES", ["Add stop-after-3-failed-attempts rule",
                       "Add check-the-obvious-first and backward tracing technique"]),
    34: ("PARTIAL", "MAYBE", ["Trim overview to shorter trigger; shorten iron law"]),
    35: ("YES", "YES", ["Compress to 4-step flow REPRODUCE/ISOLATE/UNDERSTAND/FIX with one-change-at-a-time rule"]),
    36: ("YES", "PARTIAL", ["Anchor as anti-pattern guard and add escalation rule"]),
    37: ("PARTIAL", "NO", []),
    38: ("YES", "PARTIAL", ["Require minimal reproducible case; never fix what you cannot reproduce"]),
    39: ("YES", "PARTIAL", ["Force ordered steps Read-error/Understand-code/Identify-root-cause/Fix-and-verify"]),
    40: ("YES", "YES", ["Frame as scientific method with OBSERVE/HYPOTHESIZE/PREDICT and environment-specific repro conditions"]),
    41: ("YES", "YES", ["Add explicit Verification phase and Related Skills routing",
                       "Add supporting references plus red flags"]),
    42: ("PARTIAL", "MAYBE", ["Add Core Principle section with process-violation flags"]),
    43: ("YES", "YES", ["Add The 3-Fix Rule; preserve core principle while compressing"]),
    44: ("YES", "PARTIAL", ["Translate and restructure to a distinct language variant"]),
    45: ("YES", "YES", ["Add Three-fix circuit breaker + red flags as return-to-phase-1"]),
    46: ("YES", "MAYBE", ["Rebuild as disciplined evidence framework with output format + debugging report"]),
    47: ("YES", "PARTIAL", ["Add Using-the-Debugger handler (Windows/PowerShell)"]),
    48: ("YES", "PARTIAL", ["Reduce to 4 phases each with one focused action"]),
    49: ("YES", "PARTIAL", ["Add activation signals + stabilize-report/narrow-surface/instrument phases"]),
    50: ("NO", "NO", []),
    51: ("YES", "PARTIAL", ["Add git bisect workflow to isolate failure commit"]),
    52: ("YES", "PARTIAL", ["Add 5-step order with scale-depth-to-problem guidance"]),
    53: ("YES", "YES", ["Compress into Core-Rule + Workflow + When-stuck; add stop-when-stuck rule"]),
    54: ("YES", "YES", ["Add Emergency Stop Rule + orientation with use/don't-use boundaries"]),
    55: ("YES", "PARTIAL", ["Adapt iron law into never-guess and resist-impulse"]),
    56: ("YES", "YES", ["Add single-hypothesis test escape clause: 3 failed fixes = framing is wrong"]),
    57: ("YES", "MAYBE", ["Add Invocation + Refuse Gate (do not proceed without prerequisites)"]),
    58: ("YES", "YES", ["Add stop conditions + 5-step loop; stop after bad guesses"]),
    59: ("YES", "PARTIAL", ["Import Fagan Inspection methodology as novel workflow"]),
    60: ("YES", "PARTIAL", ["Rebuild as first-person What-I-Do phases REPRODUCE/ISOLATE/IDENTIFY/FIX"]),
    61: ("YES", "MAYBE", ["Start with evidence-not-guesses; minimal repro command rule"]),
    62: ("YES", "PARTIAL", ["Add disciplined loop + anti-patterns + when-stuck"]),
    63: ("YES", "YES", ["Add one-hypothesis-at-a-time + falsify via instrumentation"]),
    64: ("YES", "PARTIAL", ["Add reproduction gate sign-off + feedback-loop quality criteria"]),
    65: ("YES", "PARTIAL", ["Add Key Rules + Tool Use sections"]),
    66: ("YES", "PARTIAL", ["Add Debugging Commands section + 4-phase repro/isolate/identify/fix"]),
    67: ("YES", "YES", ["Add Three-Attempt Cap + trigger conditions"]),
    68: ("YES", "YES", ["Add checklist of anti-patterns + techniques-by-symptom + invariant rules with context-budget note"]),
    69: ("YES", "MAYBE", ["Add reproduce-or-don't-fix rule; unstructured but strong"]),
    70: ("YES", "MAYBE", ["Korean-language rebuild; mandatory phases + critical rules"]),
    71: ("YES", "PARTIAL", ["Route to debug-assistant escalation + command safety"]),
    72: ("YES", "PARTIAL", ["Add ranked-hypotheses + cheapest-falsification-check rule"]),
    73: ("YES", "PARTIAL", ["Add Evidence-First + One-Variable-at-a-Time core principles"]),
    74: ("YES", "PARTIAL", ["Add goals / hard rules / read-first structure"]),
    75: ("YES", "PARTIAL", ["Add git bisect isolation workflow"]),
    76: ("YES", "PARTIAL", ["Build as project-specific surfaces + guardrails with workflow"]),
    77: ("YES", "PARTIAL", ["Add 5-step loop never-skip rule"]),
    78: ("YES", "PARTIAL", ["Add procedure + example; minimal"]),
    79: ("YES", "PARTIAL", ["Minimal loop + output; evidence-first"]),
    80: ("YES", "MAYBE", ["Given project-specific; preserve iron law"]),
    81: ("YES", "MAYBE", ["Restructured workflow with explicit trigger"]),
    82: ("YES", "MAYBE", ["Evidence-gathering phase dedicated"]),
    83: ("YES", "PARTIAL", ["Add instrument/photograph-instrument loop before hypothesizing"]),
    84: ("YES", "MAYBE", ["Compact with invoke/refuse gate"]),
    85: ("YES", "MAYBE", ["Given project-specific commands"]),
}


def main() -> None:
    rows = json.loads((OUT / "group_records.json").read_text(encoding="utf-8"))
    for record in rows:
        gid = record["group_id"]
        meaning, worth, motifs = CODING.get(gid, ("NO", "NO", []))
        record["meaningful_behavior_change"] = meaning
        record["worth_reviewing"] = worth
        record["motif_1"] = motifs[0] if motifs else ""
        record["motif_2"] = motifs[1] if len(motifs) > 1 else ""
        record["motif_3"] = motifs[2] if len(motifs) > 2 else ""
    (OUT / "group_records_annotated.json").write_text(
        json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    with (OUT / "systematic-debugging-group-worksheet.tsv").open(
            "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    print("meaningful:", Counter(r["meaningful_behavior_change"] for r in rows))
    print("worth:", Counter(r["worth_reviewing"] for r in rows))
    print("motif-bearing groups:", sum(1 for r in rows if r["motif_1"]))
    print("annotated groups:", len(rows))


if __name__ == "__main__":
    main()
