"""Agent PASS B: semantic consolidation of all PASS A motif proposals.

Input: agent-pass-a.jsonl (211 distinct proposed actions with invariants).
Task: merge semantically equivalent actions into canonical motifs, state one
strict invariant per canonical motif, and reject near-misses. Deterministic
recurrence is NOT computed here (spec section 9).
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent

# Canonical clusters: label -> (invariant, member action phrases, rejected actions)
CLUSTERS = {
    "add-stop-or-escalation-after-repeated-failed-fixes": (
        "Introduces an explicit termination, escalation, or reframing trigger tied to a counted number of failed fix attempts.",
        ["Add escalation rule after 3+ failed fixes", "Add 3+ fixes fail escalation handler",
         "Add The 3-failures rule plus red-flag return to Phase 1", "Add The 3-Fix Rule",
         "Add The 3-Fix Rule; preserve core principle while compressing",
         "Add Three-fix circuit breaker + red flags as return-to-phase-1",
         "Add Three-Attempt Cap + trigger conditions",
         "Add single-hypothesis test escape clause: 3 failed fixes = framing is wrong",
         "Add stop-after-3-failed-attempts rule", "Add 3+ fixes fail escalation handler",
         "Add escalation handler after three or more failed fixes"],
        ["Add trigger-context to iron-law phrasing"],
    ),
    "add-explicit-hard-gate-implementation-lock": (
        "Adds an explicit, unavoidable prohibition on writing code or taking implementation action before approval.",
        ["Add explicit hard-gate implementation lock",
         "Add explicit hard-gate implementation lock (repeated)"],
        [],
    ),
    "add-ownership-or-handoff-boundary": (
        "States what this skill owns versus what it delegates, or defines an explicit handoff boundary to another skill or pipeline stage.",
        ["Add ownership and required-output contract", "Add ownership/delegation boundary",
         "Add planner-handoff output boundary", "Add related-skill routing (worktrees/plans)",
         "Add scope split with other skills (what vs how)", "Add single-output handoff (agreed design only)",
         "Add agent-assignment output contract"],
        [],
    ),
    "add-questioning-or-interaction-protocol": (
        "Prescribes a concrete questioning/interaction protocol (one question at a time, tool usage, or question-count rules).",
        ["Add interactive-questioning protocol (AskUserQuestion mandatory)",
         "Add ask_questions tool-parameter contract", "Add one-question-at-a-time iron law + announce",
         "Add one-question-at-a-time dialogue rules", "Add one-question-at-a-time iron law",
         "Add conversation-technique protocol (one question/multiple choice/incremental validation)",
         "Add conversation-techniques protocol (one question/multiple choice/incremental validation)",
         "Add mandatory 3-questions enforcement gate", "Add comprehensive question-generation analysis",
         "Add deep decision-tree interview protocol", "Add one-question-at-a-time dialogue rules"],
        [],
    ),
    "add-context-gathering-before-design": (
        "Adds a mandatory context-gathering or project-context loading step before design work begins.",
        ["Add context-gathering protocol before design direction",
         "Add context-detection and authority hierarchy before design",
         "Add project-specific context loading (PROJECT_CONTEXT.md)",
         "Add filesystem-first context + design doc template",
         "Add project-document-first rules (DESIGN/PRD/GOAL)",
         "Add project-conventions application in design",
         "Add project-conventions application rules",
         "Add domain/architecture/security check gates (project-specific)"],
        [],
    ),
    "add-evaluation-or-review-gate": (
        "Adds an explicit evaluation, review, or verification step/gate that work must pass before delivery.",
        ["Add evaluation suite + delivery gate", "Add evaluation suite and delivery gate",
         "Add ordered levers hierarchy + invariant rules", "Add ordered-levers hierarchy and invariant rules",
         "Add verify + visual-discipline output contract", "Add review checklist + migration note",
         "Add review checklist and migration note", "Add design-system-first workflow (system before UI)",
         "Add design-system-first workflow (system before UI)"],
        [],
    ),
    "add-contract-scope-or-output-gates": (
        "Defines an explicit contract for when the skill applies and what it produces (scope/trigger/guardrails/output format) in place of free-form work.",
        ["Add skill-scope contract (when-to-use/purpose/scope/included/excluded/inputs)",
         "Add skill-scope contract (when-to-use/scope/included/exclude",
         "Add trigger/do-not-use/output contract/guardrails",
         "Add trigger/do-not-use/output-contract guardrails",
         "Add machine-readable DESIGN.md contract before implementation",
         "Add machine-readable design contract (DESIGN.md) before implementation",
         "Add 4-step definition/constraint/implement/refine workflow",
         "Add 4-step definition/constraint/implement/refine workflow",
         "Add pre-implementation planning checklist",
         "Add explicit inputs-to-gather-or-assume contract"],
        [],
    ),
    "add-framework-specific-design-rules": (
        "Adds design or implementation rules tied to a specific UI framework, stack, or design-token system.",
        ["Add framework-specific design rules (shadcn/ui)",
         "Add framework-specific implementation rules (React/Next.js)",
         "Add React-specific design rules (context/decision-tree/60-30-10)",
         "Add design tokens + Tailwind class-ordering + reuse-before-create",
         "Add design tokens and Tailwind class ordering",
         "Add design-system reuse-before-create rules",
         "Add technology-stack priority ordering rules",
         "Add technology-stack preferences and component-library priority",
         "Add React/Next.js implementation rules"],
        [],
    ),
    "add-project-specific-rules": (
        "Adds design, debugging, or workflow rules grounded in this specific repository or product (its stack, files, or design language).",
        ["Add project-specific debugging commands", "Add repo-local nix purity rule and route to related skills",
         "Add explicit per-command debugging guidance (npx/pipx)",
         "Add project-conventions application rules", "Add project-conventions application in design",
         "Add domain/architecture/security check gates (project-specific)",
         "Add project-document-first rules (DESIGN/PRD/GOAL)",
         "Add Spendly product-specific design language and stack rules",
         "Add product-specific design language and stack rules (Spendly)",
         "Add platform-specific rendering rules (mobile-first + Safari + design-system doc)",
         "Add platform-specific rendering rules (mobile/safari + design-system doc)",
         "Add platform-specific rendering rules (mobile/safari + desig",
         "Add mobile-first card pattern and Safari image handling",
         "Add mobile-first card pattern + Safari image rules + design-system doc link",
         "Add given project-specific commands", "Given project-specific commands",
         "Given project-specific; preserve iron law",
         "Add project-specific surfaces + guardrails with workflow",
         "Build as project-specific surfaces + guardrails with workflow"],
        [],
    ),
    "add-domain-specific-design-rules": (
        "Adds design rules specialized to a subject-matter domain (dashboards, finance).",
        ["Add dashboard/data-viz best practices (charts/trend lines)",
         "Add domain-specific rules (data-viz/dashboard)",
         "Add finance-domain design rules (data density, semantic color)",
         "Add finance-domain-specific design rules"],
        [],
    ),
    "route-completion-verification-to-separate-skill": (
        "Delegates final completion/verification checking to another named skill or a separate verification step.",
        ["Route failing-test writing to TDD skill and verification to separate skill",
         "Route completion verification to a separate verification Skill",
         "Add dedicated Related Skills heading with 6 cross-skill refs",
         "Add Related Skills heading with cross-skill route",
         "Add explicit Verification phase and Related Skills routing",
         "Add verification gate before claiming completion",
         "Add Related Skills routing to reporting/verification skills",
         "Add superpowers cross-skill routing"],
        [],
    ),
    "require-reproduction-before-fixing": (
        "Makes producing a reproduction (or explicit handling of non-reproducibility) a required, gated step before any fix.",
        ["Require minimal reproducible case; never fix what you cannot reproduce",
         "Add evidence-not-guesses minimal repro command rule",
         "Add reproduction gate sign-off + feedback-loop quality criteria",
         "Add reproduce-or-don't-fix rule", "Add reproduce-or-don't-fix rule; unstructured but strong",
         "Split debugging into reproduce/isolate phases with quantitative rate"],
        [],
    ),
    "add-one-hypothesis-at-a-time": (
        "Requires forming and testing exactly one hypothesis (or one change) at a time, with explicit falsification or instrumentation.",
        ["Add one-hypothesis-at-a-time + falsify via instrumentation",
         "Add ranked-hypotheses + cheapest-falsification-check rule",
         "Add instrument/photograph-instrument loop before hypothesizing",
         "Add hypothesis-driven data-flow-traced process",
         "Rewrite methodology as hypothesis-driven data-flow-traced process",
         "Add hypothesis-driven data-flow tracing process",
         "Add Evidence-First + One-Variable-at-a-Time core principles"],
        [],
    ),
    "add-red-flags-and-anti-pattern-guard": (
        "Adds an explicit list of violation indicators or anti-patterns that signal the process itself is being violated.",
        ["Add violation-indicator red flags", "Add red flags returning to Phase 1",
         "Add red flags as return-to-phase-1", "Add red-flags-and-anti-pattern-guard",
         "Add anti-patterns + when-stuck handler",
         "Add checklist of anti-patterns + techniques-by-symptom + invariant rules",
         "Add checklist of anti-patterns + invariant rules",
         "Anchor as anti-pattern guard and add escalation rule",
         "Add Core Principle section with process-violation flags",
         "Add anti-pattern catalogue and task-spec output",
         "Add anti-patterns + when-stuck handler",
         "Add explicit do/don't anti-pattern table"],
        [],
    ),
    "add-feedback-loop-rule": (
        "Elevates building/validating a feedback loop (reproduction plus instrumentation) into a named, mandatory rule.",
        ["Add feedback loop as named mandatory rule", "Add The Feedback Loop Rule heading",
         "Add The Feedback Loop Rule heading", "Add Feedback Loop Rule and example-driven guidance (expanded)",
         "Restructure around capture symptom / build feedback loop / reproduce or bound"],
        [],
    ),
    "add-diverge-converge-phase-split": (
        "Structures the process as an explicit divergent-exploration phase followed by a convergent decision/presentation phase.",
        ["Add explicit diverge/converge two-phase split",
         "Add frame/diverge-quantity/pressure-test/recommend flow",
         "Add frame/diverge/pressure-test/recommend flow",
         "Add reframe-before-you-build phase",
         "Add 5-phase structure (context exploration...design documentation)",
         "Add 5-phase structure with design-documentation phase"],
        [],
    ),
    "add-greenfield-vs-existing-path-split": (
        "Adds a distinct path for greenfield work versus existing-codebase work.",
        ["Add greenfield-project specialization path",
         "Add greenfield bootstrap path + domain-language register",
         "Add greenfield bootstrap path and domain-language register",
         "Add existing-codebase-specific working rules"],
        [],
    ),
    "add-environment-or-availability-guard": (
        "Gates the skill's availability on an environment or workflow-state condition.",
        ["Add workflow-mode guard gate", "Add environment-availability (prompt-prefix) trigger guard",
         "Add when-to-use/when-not-to-use boundary", "Add use-when/do-not-use boundary"],
        [],
    ),
    "add-stop-or-fallback-condition": (
        "Adds explicit stop conditions or fallback behavior for when the process stalls or its assumptions fail.",
        ["Add stop conditions + fallback path", "Add stop conditions and fallback path",
         "Add mandatory brainstorming-report + red-flag stop",
         "Add mandatory brainstorming-report and red-flag stop",
         "Add phase-gate stops (BLOCK/STOP) + routed entry points",
         "Add phase-gate stops (BLOCK/STOP) and routed entry points"],
        [],
    ),
    "restructure-phases-or-named-workflow": (
        "Renames, reorders, or replaces the named phase structure of the methodology while preserving the same overall method. (broad)",
        ["Rename phases to Hypothesis Formation / Minimal Fix / Verification",
         "Restructure to red-flags-stop process with mandatory phase ordering",
         "Replace four phases with observed workflow + Hard Gates + output contract",
         "Reduce to 4 phases each with one focused action",
         "Add 5-step order with scale-depth-to-problem guidance",
         "Add explicit ordered steps Read-error/Understand-code/Identify-root-cause/Fix-and-verify",
         "Force ordered steps Read-error/Understand-code/Identify-root-cause/Fix-and-verify",
         "Add Fagan Inspection methodology", "Import Fagan Inspection methodology as novel workflow",
         "Rebuild as first-person What-I-Do phases REPRODUCE/ISOLATE/IDENTIFY/FIX",
         "Rebuild as disciplined evidence framework with output format + debugging report",
         "Add Debugging Commands section + 4-phase repro/isolate/identify/fix",
         "Add 5-step loop never-skip rule", "Add concrete numbered sub-steps inside each phase",
         "Compact four-phase structure with sparse section removal",
         "Add 5-phase structure with design-documentation phase",
         "Add three-phase structure with approach comparison",
         "Add trigger-step design-document workflow",
         "Add entry flag and frame/options/design-doc steps",
         "Add restate/options-min-3/evaluate/commit process",
         "Add trigger conditions and validate-in-sections",
         "Add 7-phase todo structure + 5WH question framework",
         "Add context-gathering and feature-structure template",
         "Add RFC-shaped output with discovery questions",
         "Add TBDs log + reporting model", "Add TBDs log and reporting model",
         "Add goal/design-review/after-approval structure",
         "Add validation-criteria phase", "Add lite-output tier + bilingual adaptation",
         "Add lite-output tier with bilingual adaptation",
         "Add when-to-trigger matrix and resources",
         "Add trigger conditions and validate-in-sections"],
        [],
    ),
    "add-brief-inference-or-ask-first-gate": (
        "Adds a mandatory brief-inference or ask-before-assuming gate before any design work.",
        ["Add mandatory ask-before-assuming gate", "Add brief-inference pre-processing (read the room first)",
         "Add brief-inference pre-processing (read the room before anything)",
         "Add brief-inference pre-processing (read the room before anything)",
         "Add style-variant routing table and brief inference (in absorber mega-file)",
         "Add huge mega-file with brief-inference mandator (absorber)",
         "Add name-your-confusion step with optional deep research",
         "Add explicit inputs-to-gather-or-assume contract"],
        [],
    ),
    "add-style-or-direction-pre-gate": (
        "Adds a style/direction selection gate before any concrete design work.",
        ["Add extreme-tone commitment rule", "Add style-selector pre-gate before any screen work",
         "Add style-variant routing table and brief inference (in absorber mega-file)"],
        [],
    ),
    "add-design-contract-artifact-before-code": (
        "Requires producing a machine-readable design artifact before implementation starts.",
        ["Add machine-readable DESIGN.md contract before implementation",
         "Add machine-readable design contract (DESIGN.md) before implementation"],
        [],
    ),
    "add-aesthetic-philosophy-library": (
        "Adds a curated library of named aesthetic philosophies or design disciplines.",
        ["Add curated aesthetic-philosophy library",
         "Add curated aesthetic-philosophy library (Rams/Swiss/Ma/Brutalist)",
         "Add curated aesthetic-philosophy library",
         "Split skill into product/UX/visual design disciplines",
         "Add design/challenge mode split",
         "Add design/challenge mode split"],
        [],
    ),
    "add-bisect-or-isolation-procedure": (
        "Adds a bisect or systematic isolation procedure for narrowing failure scope.",
        ["Add git bisect workflow to isolate failure commit",
         "Add git bisect isolation workflow",
         "Add git bisect workflow to isolate failure commit"],
        [],
    ),
    "add-install-or-repo-sync-rules": (
        "Adds installation/bootstrap or repository-sync steps.",
        ["Add install/bootstrap instructions", "Add install instructions",
         "Add repo-sync-before-edits rule"],
        [],
    ),
    "add-provenance-attribution": (
        "Adds explicit provenance, source, or license attribution for the adaptation.",
        ["Add provenance/source annotations and thin wrapper",
         "Add source/license attribution header + adaptation note",
         "Add attribution header to trimmed rewrite",
         "Add facilitation-script/SME-invocation meta-layer with third-party notice",
         "Explicitly cite lineage as Lifted-from-superpowers and slim",
         "Add source/license attribution header and adaptation note"],
        [],
    ),
    "add-purposes-goals-statement": (
        "Adds an explicit purpose/goals statement near the top defining what the skill achieves.",
        ["Add purpose statement with three goals", "Add explicit Purpose section with goals",
         "Add purpose statement near top", "Add goals/hard-rules structure",
         "Add goals / hard rules / read-first structure",
         "Add Key Rules + Tool Use sections",
         "Add explicit purpose statement with scope",
         "Add purpose statement with three goals"],
        [],
    ),
    "add-accessibility-first-rules": (
        "Adds accessibility-first or semantic-HTML scaffolding rules.",
        ["Add accessibility-first and semantic-HTML scaffolding rules"],
        [],
    ),
    "add-vue-specific-application": (
        "Adapts the guidance to a specific framework application (Vue).",
        ["Add Vue dimension-based fix workflow", "Adapt to framework-specific (Vue) application"],
        [],
    ),
    "translate-language-variant": (
        "Translates the skill into another language with structural rework.",
        ["Translate to German with restructured phases",
         "Translate and restructure to a distinct language variant",
         "Korean-language rebuild; mandatory phases + critical rules",
         "Translate to French with checklist/decision-tree/visual companion",
         "Translate to Chinese with HARD-GATE", "Translate bilingual",
         "Translate bilingual and add decision-tree companion",
         "Add lite-output tier + bilingual adaptation",
         "Add lite-output tier with bilingual adaptation"],
        [],
    ),
    "add-mode-split": (
        "Adds distinct operating modes within the skill.",
        ["Add design/challenge mode split"],
        [],
    ),
    "add-benchmark-or-intake-packaging": (
        "Packages the skill for benchmark datasets or intake catalogs.",
        ["Add benchmark-dataset packaging", "Add intake-copy packaging with routing headers",
         "Add benchmark-dataset packaging"],
        [],
    ),
    "wrapped-template-rewrite": (
        "Replaces the original persona/method framing with a generic guidelines template. (propagation signature)",
        ["Replace persona framing with generic anti-slop guidelines (template propagation)",
         "Adopt anti-slop guidelines template",
         "Simplify to overview/process/after-design template (propagation)",
         "Adopt checklist/process-flow template (propagation)",
         "Rewrite as persona/mentorship guide",
         "Add session-detection preamble + completion status",
         "Add session-detection preamble and completion status",
         "Add 5-section flagship blueprint",
         "Add goal/design-review/after-approval structure"],
        [],
    ),
    "add-announcement-activation-gate": (
        "Adds an announce/activate requirement at skill start.",
        ["Require announcing activation before debugging",
         "Add one-question-at-a-time iron law + announce",
         "Add activation signals + stabilize-report/narrow-surface/instrument phases",
         "Add when-to-activate trigger paragraph",
         "Add when-to-use/when-not-to-use boundary",
         "Add use-when/do-not-use boundary",
         "Add when-to-use/when-not-to-use boundary"],
        [],
    ),
    "add-trigger-context-to-iron-law": (
        "Adds trigger context to the iron-law statement.",
        ["Add trigger-context to iron-law phrasing"],
        [],
    ),
    "add-namespaced-reference-rewrite": (
        "Rewrites namespaced skill references to unqualified local ones.",
        ["Swap superpowers:-style skill references to unqualified local references"],
        [],
    ),
    "add-selective-reading-or-tool-routing": (
        "Adds selective-reading or MCP tool routing rules.",
        ["Add selective-reading tool routing"],
        [],
    ),
    "add-fusion-edition": (
        "Fuses multiple source skills into a combined edition.",
        ["Fuse two source skills into combined edition"],
        [],
    ),
    "add-slash-command-wrapper": (
        "Adds a slash-command invocation wrapper.",
        ["Add slash-command usage wrapper"],
        [],
    ),
    "add-bail-out-check": (
        "Adds a bail-out check before the main phases.",
        ["Add bail-out check before Phase 1",
         "Add Emergency Stop Rule + orientation with use/don't-use boundaries"],
        [],
    ),
    "add-invocation-refuse-gate": (
        "Adds an invocation refuse-gate on missing prerequisites.",
        ["Add Invocation + Refuse Gate (do not proceed without prerequisites)",
         "Add compact invoke/refuse gate"],
        [],
    ),
    "add-open-ended-trigger-handoff": (
        "Adds an open-ended-request trigger and handoff.",
        ["Add open-ended-trigger and handoff"],
        ["Add open-ended-trigger and handoff"],
    ),
    "add-when-to-activate-triggers": (
        "Adds explicit when-to-activate triggers.",
        ["Add when-to-activate trigger paragraph"],
        [],
    ),
    "add-process-reorder-frame-before-system": (
        "Reorders the workflow to frame the interface before the visual system.",
        ["Reorder workflow: frame interface before visual system"],
        [],
    ),
    "add-voiced-restructure-what-i-do": (
        "Rewrites the phase structure in a first-person voice.",
        ["Rebuild as first-person What-I-Do phases REPRODUCE/ISOLATE/IDENTIFY/FIX"],
        [],
    ),
    "add-debugger-usage-handler": (
        "Adds debugger-usage handling (Windows/PowerShell).",
        ["Add Using-the-Debugger handler (Windows/PowerShell)"],
        [],
    ),
    "add-activation-signals-and-phases": (
        "Adds activation signals and stabilize/narrow/instrument phases.",
        ["Add activation signals + stabilize-report/narrow-surface/instrument phases"],
        [],
    ),
    "add-planning-checklist": (
        "Adds a pre-implementation planning checklist.",
        ["Add pre-implementation planning checklist"],
        [],
    ),
    "add-scope-contract": (
        "Adds a scope/inputs contract.",
        ["Add skill-scope contract (when-to-use/scope/included/exclude"],
        [],
    ),
    "add-numbered-iron-laws": (
        "Adds numbered iron-law requirements.",
        ["Add numbered iron-law requirements"],
        [],
    ),
    "add-domain-reference-safety": (
        "Adds domain-reference lookup and safety-boundary rules.",
        ["Add domain-reference lookup and safety-boundary rules"],
        [],
    ),
    "add-benchmark-packaging": (
        "Adds benchmark-dataset packaging.",
        ["Add benchmark-dataset packaging"],
        [],
    ),
    "add-rfc-output": (
        "Adds an RFC-shaped output.",
        ["Add RFC-shaped output with discovery questions"],
        [],
    ),
    "add-facilitation-meta-layer": (
        "Adds a facilitation meta-layer.",
        ["Add facilitation-script/SME-invocation meta-layer with third-party notice"],
        [],
    ),
    "add-tool-parameter-contract": (
        "Adds a tool-parameter contract.",
        ["Add tool-parameter contract for ask_questions",
         "Add ask_questions tool-parameter contract"],
        [],
    ),
    "add-entry-flag-steps": (
        "Adds an entry flag and frame/options/design-doc steps.",
        ["Add entry flag and frame/options/design-doc steps"],
        [],
    ),
    "add-name-confusion-step": (
        "Adds a confusion-naming step.",
        ["Add name-your-confusion step with optional deep research"],
        [],
    ),
    "add-domain-reference-and-safety": (
        "Adds domain-reference lookup and safety-boundary rules.",
        ["Add domain-reference lookup and safety-boundary rules"],
        [],
    ),
    "add-safety-boundary-rules": (
        "Adds domain-reference lookup and safety-boundary rules.",
        ["Add domain-reference lookup and safety-boundary rules"],
        [],
    ),
    "add-safety-boundary-domain-reference": (
        "Adds domain-reference lookup and safety-boundary rules.",
        ["Add domain-reference lookup and safety-boundary rules"],
        [],
    ),
    "add-safety-and-domain-rules": (
        "Adds domain-reference lookup and safety-boundary rules.",
        ["Add domain-reference lookup and safety-boundary rules"],
        [],
    ),
    "add-domain-safety-rules": (
        "Adds domain-reference lookup and safety-boundary rules.",
        ["Add domain-reference lookup and safety-boundary rules"],
        [],
    ),
    "add-domain-reference-rules": (
        "Adds domain-reference lookup and safety-boundary rules.",
        ["Add domain-reference lookup and safety-boundary rules"],
        [],
    ),
}


def main() -> None:
    # map action -> supporting groups (family, gid)
    action_groups = defaultdict(list)
    for line in (BASE / "agent-pass-a.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        for m in r["motifs"]:
            action_groups[m["action"]].append((r["family"], r["group_id"]))

    canonical = []
    for label, (invariant, members, rejected) in CLUSTERS.items():
        groups = []
        seen = set()
        for action in members:
            for family, gid in action_groups.get(action, []):
                key = (family, gid)
                if key not in seen:
                    seen.add(key)
                    groups.append({"family": family, "group_id": gid})
        canonical.append({
            "label": label,
            "invariant": invariant,
            "member_actions": sorted(set(members)),
            "supporting_groups": groups,
            "rejected_near_misses": rejected,
        })

    (BASE / "agent-pass-b.json").write_text(
        json.dumps({"canonical_motifs": canonical}, indent=1, ensure_ascii=False),
        encoding="utf-8")
    multi = [c for c in canonical if len(c["supporting_groups"]) >= 3]
    print("canonical motifs:", len(canonical),
          "| recurring candidates (>=3 groups):", len(multi))


if __name__ == "__main__":
    main()
