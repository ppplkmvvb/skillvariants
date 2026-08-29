"""Agent PASS B v2: behavior-equivalence clustering (spec sections 5-6).

Changes from v1 (driven by the over-merge audit):
- clusters are formed by BEHAVIOR equivalence, not topic similarity
- every cluster carries a behavior_signature (trigger/action/object/outcome)
- the 26-group restructure mega-cluster is split into four narrow motifs
- known near-misses moved out: design-system-first (from evaluation gate),
  4-step workflow / planning checklist (from contract gates), platform
  rendering (from project rules), discipline split (from philosophy library),
  when-not-to-use (from announcement gate), methodology rewrite (from
  one-hypothesis-at-a-time)

PASS A proposals (agent-pass-a.jsonl) are FROZEN and not relabeled.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent

# v2 clusters: label -> (invariant, behavior_signature, member action phrases)
CLUSTERS_V2 = {
    # ---------- stop / escalation family ----------
    "add-stop-or-escalation-after-repeated-failed-fixes": (
        "Introduces an explicit termination, escalation, or reframing trigger tied to a counted number of failed fix attempts.",
        {"trigger": "a counted number of failed fix attempts", "action": "stop or escalate the loop",
         "object": "debugging/iteration loop", "outcome": "agent stops or escalates instead of continuing"},
        ["Add escalation rule after 3+ failed fixes", "Add 3+ fixes fail escalation handler",
         "Add The 3-failures rule plus red-flag return to Phase 1", "Add The 3-Fix Rule",
         "Add The 3-Fix Rule; preserve core principle while compressing",
         "Add Three-fix circuit breaker + red flags as return-to-phase-1",
         "Add Three-Attempt Cap + trigger conditions",
         "Add single-hypothesis test escape clause: 3 failed fixes = framing is wrong",
         "Add stop-after-3-failed-attempts rule"],
    ),
    "add-explicit-hard-gate-implementation-lock": (
        "Adds an explicit, unavoidable prohibition on writing code or taking implementation action before approval.",
        {"trigger": "before explicit design approval", "action": "block implementation",
         "object": "code-writing/implementation", "outcome": "implementation only after gate"},
        ["Add explicit hard-gate implementation lock"],
    ),
    # ---------- scope / contract family (split from v1 contract gates) ----------
    "add-scope-or-trigger-contract": (
        "Declares when the skill applies and what it must produce via an explicit scope/trigger/non-use contract.",
        {"trigger": "skill invocation", "action": "declare scope, triggers, and non-use boundaries",
         "object": "skill applicability", "outcome": "free-form work prevented outside scope"},
        ["Add skill-scope contract (when-to-use/purpose/scope/included/excluded/inputs)",
         "Add skill-scope contract (when-to-use/scope/included/exclude",
         "Add trigger/do-not-use/output contract/guardrails",
         "Add trigger/do-not-use/output-contract guardrails"],
    ),
    "add-design-contract-artifact-before-code": (
        "Requires producing a machine-readable design artifact before implementation starts.",
        {"trigger": "before implementation", "action": "produce a design contract artifact",
         "object": "DESIGN.md / design contract", "outcome": "implementation proceeds only from contract"},
        ["Add machine-readable DESIGN.md contract before implementation",
         "Add machine-readable design contract (DESIGN.md) before implementation"],
    ),
    # ---------- context / project rules ----------
    "add-context-gathering-before-design": (
        "Adds a mandatory context-gathering or project-context loading step before design work begins.",
        {"trigger": "task start", "action": "gather or load project context first",
         "object": "project context/conventions", "outcome": "design decisions grounded in context"},
        ["Add context-gathering protocol before design direction",
         "Add context-detection and authority hierarchy before design",
         "Add project-specific context loading (PROJECT_CONTEXT.md)",
         "Add filesystem-first context + design doc template",
         "Add project-document-first rules (DESIGN/PRD/GOAL)",
         "Add project-conventions application in design",
         "Add project-conventions application rules",
         "Add domain/architecture/security check gates (project-specific)"],
    ),
    "add-project-or-product-specific-design-rules": (
        "Adds design or debugging rules grounded in this specific repository, product, or its design language.",
        {"trigger": "working in the target repo/product", "action": "apply repo/product-specific rules",
         "object": "design and workflow decisions", "outcome": "output matches the specific project"},
        ["Add project-specific debugging commands", "Add repo-local nix purity rule and route to related skills",
         "Add explicit per-command debugging guidance (npx/pipx)",
         "Add Spendly product-specific design language and stack rules",
         "Add product-specific design language and stack rules (Spendly)",
         "Add given project-specific commands", "Given project-specific commands",
         "Given project-specific; preserve iron law",
         "Add project-specific surfaces + guardrails with workflow",
         "Build as project-specific surfaces + guardrails with workflow"],
    ),
    "add-platform-rendering-rules": (
        "Adds rendering or compatibility rules for specific platforms/browsers/devices.",
        {"trigger": "UI implementation", "action": "apply platform-specific rendering rules",
         "object": "mobile/Safari rendering", "outcome": "cross-platform correctness"},
        ["Add platform-specific rendering rules (mobile/safari + desig",
         "Add platform-specific rendering rules (mobile-first + Safari + design-system doc)",
         "Add mobile-first card pattern and Safari image handling",
         "Add mobile-first card pattern + Safari image rules + design-system doc link"],
    ),
    # ---------- framework / stack rules ----------
    "add-framework-specific-design-rules": (
        "Adds design or implementation rules tied to a specific UI framework, stack, or design-token system.",
        {"trigger": "working within a named stack", "action": "apply framework/stack-specific rules",
         "object": "UI framework usage", "outcome": "idiomatic, consistent output for that stack"},
        ["Add framework-specific design rules (shadcn/ui)",
         "Add framework-specific implementation rules (React/Next.js)",
         "Add React-specific design rules (context/decision-tree/60-30-10)",
         "Add design tokens + Tailwind class-ordering + reuse-before-create",
         "Add design tokens and Tailwind class ordering",
         "Add design-system reuse-before-create rules",
         "Add technology-stack priority ordering rules",
         "Add technology-stack preferences and component-library priority",
         "Add React/Next.js implementation rules"],
    ),
    "add-vue-specific-application": (
        "Adapts the guidance to a specific framework application (Vue).",
        {"trigger": "Vue project", "action": "apply Vue-specific fixes", "object": "Vue components",
         "outcome": "framework-correct output"},
        ["Add Vue dimension-based fix workflow", "Adapt to framework-specific (Vue) application"],
    ),
    # ---------- review / verification family (narrowed) ----------
    "add-evaluation-or-review-gate": (
        "Adds an explicit evaluation, review, or verification step/gate that work must pass before delivery.",
        {"trigger": "work produced", "action": "evaluate/review against defined criteria",
         "object": "produced output", "outcome": "delivery only after gate passes"},
        ["Add evaluation suite + delivery gate", "Add evaluation suite and delivery gate",
         "Add ordered levers hierarchy + invariant rules", "Add ordered-levers hierarchy and invariant rules",
         "Add verify + visual-discipline output contract", "Add review checklist + migration note",
         "Add review checklist and migration note"],
    ),
    "add-design-system-first-workflow": (
        "Reorders the workflow to build the design system before individual UI work.",
        {"trigger": "UI task start", "action": "build design system first", "object": "design system",
         "outcome": "UI composed from established system"},
        ["Add design-system-first workflow (system before UI)",
         "Add design-system-first workflow (system before UI)"],
    ),
    "add-aesthetic-philosophy-library": (
        "Adds a curated library of named aesthetic philosophies for direction choice.",
        {"trigger": "aesthetic direction phase", "action": "choose from named philosophies",
         "object": "aesthetic direction", "outcome": "deliberate style commitment"},
        ["Add curated aesthetic-philosophy library",
         "Add curated aesthetic-philosophy library (Rams/Swiss/Ma/Brutalist)"],
    ),
    "split-skill-into-design-disciplines": (
        "Splits the skill into separate named design disciplines (product/UX/visual).",
        {"trigger": "design task", "action": "separate disciplines", "object": "design concerns",
         "outcome": "each discipline addressed distinctly"},
        ["Split skill into product/UX/visual design disciplines",
         "Split skill into product/UX/visual design disciplines"],
    ),
    # ---------- verification routing (SD) ----------
    "route-completion-verification-to-separate-skill": (
        "Delegates final completion/verification checking to another named skill or a separate verification step.",
        {"trigger": "fix implemented", "action": "delegate verification to another skill/step",
         "object": "completion/verification", "outcome": "claims verified externally"},
        ["Route failing-test writing to TDD skill and verification to separate skill",
         "Route completion verification to a separate verification Skill",
         "Add dedicated Related Skills heading with 6 cross-skill refs",
         "Add Related Skills heading with cross-skill route",
         "Add explicit Verification phase and Related Skills routing",
         "Add verification gate before claiming completion",
         "Add Related Skills routing to reporting/verification skills",
         "Add superpowers cross-skill routing"],
    ),
    "add-domain-specific-design-rules": (
        "Adds design rules specialized to a subject-matter domain (dashboards, finance).",
        {"trigger": "domain-specific UI task", "action": "apply domain rules",
         "object": "domain-specific UI patterns", "outcome": "domain-appropriate output"},
        ["Add dashboard/data-viz best practices (charts/trend lines)",
         "Add domain-specific rules (data-viz/dashboard)",
         "Add finance-domain design rules (data density, semantic color)",
         "Add finance-domain-specific design rules"],
    ),
    # ---------- reproduction / hypothesis family (SD, narrowed) ----------
    "require-reproduction-before-fixing": (
        "Makes producing a reproduction (or explicit handling of non-reproducibility) a required, gated step before any fix.",
        {"trigger": "bug reported", "action": "require reproduction first", "object": "failure reproduction",
         "outcome": "no fix without repro"},
        ["Require minimal reproducible case; never fix what you cannot reproduce",
         "Add evidence-not-guesses minimal repro command rule",
         "Add reproduction gate sign-off + feedback-loop quality criteria",
         "Add reproduce-or-don't-fix rule", "Add reproduce-or-don't-fix rule; unstructured but strong",
         "Split debugging into reproduce/isolate phases with quantitative rate"],
    ),
    "add-one-hypothesis-at-a-time": (
        "Requires forming and testing exactly one hypothesis (or one change) at a time, with explicit falsification.",
        {"trigger": "hypothesis formation", "action": "test one hypothesis/change at a time",
         "object": "candidate fixes", "outcome": "isolated causal knowledge"},
        ["Add one-hypothesis-at-a-time + falsify via instrumentation",
         "Add ranked-hypotheses + cheapest-falsification-check rule"],
    ),
    "add-brief-inference-or-ask-first-gate": (
        "Adds a mandatory brief-inference or ask-before-assuming gate before any design work.",
        {"trigger": "ambiguous or incomplete brief", "action": "infer the brief or ask",
         "object": "task understanding", "outcome": "no assumptions carried into design"},
        ["Add mandatory ask-before-assuming gate", "Add brief-inference pre-processing (read the room first)",
         "Add brief-inference pre-processing (read the room before anything)",
         "Add name-your-confusion step with optional deep research",
         "Add explicit inputs-to-gather-or-assume contract"],
    ),
    "add-feedback-loop-rule": (
        "Elevates building/validating a feedback loop (reproduction plus instrumentation) into a named, mandatory rule.",
        {"trigger": "investigation phase", "action": "build/validate a feedback loop",
         "object": "repro + instrumentation", "outcome": "evidence loop before hypotheses"},
        ["Add feedback loop as named mandatory rule", "Add The Feedback Loop Rule heading",
         "Add Feedback Loop Rule and example-driven guidance (expanded)",
         "Restructure around capture symptom / build feedback loop / reproduce or bound"],
    ),
    # ---------- red flags / boundaries ----------
    "add-red-flags-and-anti-pattern-guard": (
        "Adds an explicit list of violation indicators or anti-patterns that signal the process itself is being violated.",
        {"trigger": "process under way", "action": "check violation indicators", "object": "own process",
         "outcome": "self-correction on violation"},
        ["Add violation-indicator red flags", "Add red flags returning to Phase 1",
         "Add red flags as return-to-phase-1", "Add anti-patterns + when-stuck handler",
         "Add checklist of anti-patterns + invariant rules",
         "Anchor as anti-pattern guard and add escalation rule",
         "Add Core Principle section with process-violation flags",
         "Add explicit do/don't anti-pattern table"],
    ),
    "add-routing-boundary-use-case": (
        "Adds explicit boundaries declaring when the skill must not be used or when it must hand off.",
        {"trigger": "out-of-scope request", "action": "decline or hand off", "object": "skill applicability",
         "outcome": "skill not used outside its boundary"},
        ["Add explicit routing boundary: do not use outside debugging",
         "Add Emergency Stop Rule + orientation with use/don't-use boundaries",
         "Add bail-out check before Phase 1",
         "Add Invocation + Refuse Gate (do not proceed without prerequisites)",
         "Add compact invoke/refuse gate"],
    ),
    # ---------- brainstorming process structure ----------
    "add-questioning-or-interaction-protocol": (
        "Prescribes a concrete questioning/interaction protocol (one question at a time, tool usage, or question-count rules).",
        {"trigger": "dialogue with user", "action": "follow questioning protocol", "object": "user interaction",
         "outcome": "structured elicitation"},
        ["Add interactive-questioning protocol (AskUserQuestion mandatory)",
         "Add ask_questions tool-parameter contract", "Add tool-parameter contract for ask_questions",
         "Add one-question-at-a-time iron law + announce", "Add one-question-at-a-time iron law",
         "Add one-question-at-a-time dialogue rules",
         "Add conversation-technique protocol (one question/multiple choice)",
         "Add conversation-techniques protocol (one question/multiple choice/incremental validation)",
         "Add mandatory 3-questions enforcement gate", "Add comprehensive question-generation analysis",
         "Add deep decision-tree interview protocol"],
    ),
    "add-diverge-converge-phase-split": (
        "Structures the process as an explicit divergent-exploration phase followed by a convergent decision/presentation phase.",
        {"trigger": "ideation phase", "action": "diverge then converge", "object": "options/approaches",
         "outcome": "explored spread before commitment"},
        ["Add explicit diverge/converge two-phase split",
         "Add frame/diverge-quantity/pressure-test/recommend flow",
         "Add frame/diverge/pressure-test/recommend flow",
         "Add reframe-before-you-build phase"],
    ),
    "add-5-phase-structured-process": (
        "Adds an explicitly numbered 5-phase structured process with documentation output.",
        {"trigger": "process start", "action": "follow 5 named phases", "object": "brainstorming process",
         "outcome": "documented design output"},
        ["Add 5-phase structure (context exploration...design documentation)",
         "Add 5-phase structure with design-documentation phase",
         "Add three-phase structure with approach comparison",
         "Add 7-phase todo structure + 5WH question framework"],
    ),
    "add-greenfield-vs-existing-path-split": (
        "Adds a distinct path for greenfield work versus existing-codebase work.",
        {"trigger": "project type detected", "action": "branch greenfield vs existing path",
         "object": "context exploration", "outcome": "appropriate exploration depth"},
        ["Add greenfield-project specialization path",
         "Add greenfield bootstrap path + domain-language register",
         "Add greenfield bootstrap path and domain-language register",
         "Add existing-codebase-specific working rules"],
    ),
    # ---------- governance ----------
    "add-ownership-or-handoff-boundary": (
        "States what this skill owns versus what it delegates, or defines an explicit handoff boundary to another skill or pipeline stage.",
        {"trigger": "stage transition or scope question", "action": "declare ownership/handoff",
         "object": "stage responsibilities", "outcome": "clean pipeline boundaries"},
        ["Add ownership and required-output contract", "Add ownership/delegation boundary",
         "Add planner-handoff output boundary", "Add related-skill routing (worktrees/plans)",
         "Add scope split with other skills (what vs how)", "Add single-output handoff (agreed design only)",
         "Add agent-assignment output contract"],
    ),
    "add-stop-or-fallback-condition": (
        "Adds explicit stop conditions or fallback behavior for when the process stalls or its assumptions fail.",
        {"trigger": "process stall or failed assumption", "action": "stop or fall back",
         "object": "brainstorming process", "outcome": "documented fallback"},
        ["Add stop conditions + fallback path", "Add stop conditions and fallback path",
         "Add mandatory brainstorming-report + red-flag stop",
         "Add mandatory brainstorming-report and red-flag stop",
         "Add phase-gate stops (BLOCK/STOP) + routed entry points",
         "Add phase-gate stops (BLOCK/STOP) and routed entry points"],
    ),
    "add-workflow-mode-guard": (
        "Gates the skill's availability on an environment or workflow-state condition.",
        {"trigger": "environment/workflow state", "action": "guard availability", "object": "skill activation",
         "outcome": "skill runs only in intended mode"},
        ["Add workflow-mode guard gate", "Add environment-availability (prompt-prefix) trigger guard"],
    ),
    "add-when-not-to-use-boundary": (
        "Adds explicit when-not-to-use boundaries for the skill.",
        {"trigger": "request outside skill purpose", "action": "decline activation", "object": "skill activation",
         "outcome": "skill not invoked for wrong tasks"},
        ["Add when-to-use/when-not-to-use boundary", "Add use-when/do-not-use boundary",
         "Add when-to-activate trigger paragraph"],
    ),
    "add-traceability-or-spec-output-rule": (
        "Mandates a specific spec/artifact output structure or a traceability requirement the design must satisfy.",
        {"trigger": "design finalized", "action": "trace/spec-structure the output", "object": "design spec",
         "outcome": "traceable, structured spec"},
        ["Add requirement-traceability hard rule (B#/F#)",
         "Add problem/solution/user-stories spec structure"],
    ),
    "add-rationalization-and-recovery": (
        "Adds a rationalization catalogue plus post-violation recovery steps.",
        {"trigger": "rationalization detected", "action": "recover after violation", "object": "own process",
         "outcome": "process restored after violation"},
        ["Add rationalization catalogue + post-violation recovery",
         "Add rationalization catalogue and post-violation recovery"],
    ),
    "add-session-detection-preamble": (
        "Adds a generated preamble with session detection and completion status.",
        {"trigger": "session start", "action": "run detection preamble", "object": "session state",
         "outcome": "status reported before work"},
        ["Add session-detection preamble + completion status",
         "Add session-detection preamble and completion status"],
    ),
    "add-progress-tracking": (
        "Adds progress tracking or TBD logging to the process.",
        {"trigger": "process under way", "action": "track progress/TBDs", "object": "process state",
         "outcome": "visible progress record"},
        ["Add progress-tracking + when-to-use contract", "Add restate-goal + missing-constraints step",
         "Add TBDs log + reporting model", "Add TBDs log and reporting model"],
    ),
    # ---------- SD-specific structure ----------
    "preserve-root-cause-first-while-compressing": (
        "Substantially shortens the document while explicitly retaining the root-cause-first governing rule.",
        {"trigger": "compression edit", "action": "shorten while keeping the iron law",
         "object": "skill document", "outcome": "brevity without losing the invariant"},
        ["Preserve iron law while trimming to loop + stop conditions",
         "Compress into Core-Rule + Workflow + When-stuck; add stop-when-stuck rule",
         "Compress to 4-step flow REPRODUCE/ISOLATE/UNDERSTAND/FIX with one-change-at-a-time rule",
         "Compress to 4-step REPRODUCE/ISOLATE/UNDERSTAND/FIX with one-change-at-a-time rule",
         "Adapt iron law into never-guess and resist-impulse",
         "Adapt iron law into never-guess and resist-impulse phrasing",
         "Add The 3-Fix Rule; preserve core principle while compressing",
         "Trim overview to shorter trigger; shorten iron law"],
    ),
    "replace-with-named-methodology": (
        "Replaces the four-phase method with a different named methodology or scientific framing.",
        {"trigger": "method redesign", "action": "adopt a named methodology", "object": "debugging method",
         "outcome": "different but equivalent method"},
        ["Add Fagan Inspection methodology", "Import Fagan Inspection methodology as novel workflow",
         "Frame as scientific method with OBSERVE/HYPOTHESIZE/PREDICT and environment-specific repro",
         "Rebuild as disciplined evidence framework with output format + debugging report",
         "Rewrite methodology as hypothesis-driven data-flow-traced process",
         "Add hypothesis-driven data-flow-traced process", "Add hypothesis-driven data-flow tracing process",
         "Rebuild as first-person What-I-Do phases REPRODUCE/ISOLATE/IDENTIFY/FIX"],
    ),
    "add-git-bisect-isolation": (
        "Adds a bisect or systematic isolation procedure for narrowing failure scope.",
        {"trigger": "unlocalized failure", "action": "bisect/isolate", "object": "failure scope",
         "outcome": "narrowed failing commit/area"},
        ["Add git bisect workflow to isolate failure commit", "Add git bisect isolation workflow"],
    ),
    "add-check-obvious-first-technique": (
        "Adds explicit cheap-checks-first and backward tracing techniques.",
        {"trigger": "investigation start", "action": "check obvious causes first", "object": "candidate causes",
         "outcome": "cheap checks before deep tracing"},
        ["Add check-the-obvious-first and backward tracing technique",
         "Add check-the-obvious-first and backward tracing technique"],
    ),
    # ---------- remaining single/small groups (kept explicit) ----------
    "add-workflow-mode-guard": (None, {}, []),  # placeholder removed below
}
# remove placeholder
CLUSTERS_V2 = {k: v for k, v in CLUSTERS_V2.items() if v[0] is not None}


def main() -> None:
    action_groups = defaultdict(list)
    for line in (BASE / "agent-pass-a.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        for m in r["motifs"]:
            action_groups[m["action"]].append((r["family"], r["group_id"]))

    canonical = []
    for label, (invariant, signature, members) in CLUSTERS_V2.items():
        groups, seen = [], set()
        for action in members:
            for family, gid in action_groups.get(action, []):
                key = (family, gid)
                if key not in seen:
                    seen.add(key)
                    groups.append({"family": family, "group_id": gid})
        canonical.append({
            "label": label,
            "invariant": invariant,
            "behavior_signature": signature,
            "member_actions": sorted(set(members)),
            "supporting_groups": groups,
        })

    (BASE / "agent-pass-b-proposed.json").write_text(
        json.dumps({"schema_version": "v2-behavior-equivalence",
                    "canonical_motifs": canonical},
                   indent=1, ensure_ascii=False), encoding="utf-8")
    recurring = [c for c in canonical if len(c["supporting_groups"]) >= 3]
    print("proposed canonical:", len(canonical),
          "| >=3 groups:", len(recurring),
          "| >=8 groups (mandatory verifier):",
          sum(1 for c in canonical if len(c["supporting_groups"]) > 8))


if __name__ == "__main__":
    main()
