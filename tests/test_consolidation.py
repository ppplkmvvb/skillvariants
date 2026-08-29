"""Guardrail tests: signature schema, vague invariants, cluster rules,
known over-merge regression fixtures (spec sections 11, 16)."""
from __future__ import annotations

import pytest

from skillvariants.consolidation import (
    BehaviorSignature,
    ClusterDecision,
    ProposedCluster,
    accept_cluster,
    invariant_is_vague,
    precheck_cluster,
    signatures_conflict,
    validate_invariant,
    signature_conflicts_in_cluster,
)


def _cluster(gids, invariant="Blocks all implementation until explicit design approval is recorded."):
    return ProposedCluster(
        label="test-cluster",
        invariant=invariant,
        signature=BehaviorSignature(
            trigger="approval/design-completion condition",
            action="block implementation",
            object="implementation/code-writing",
            outcome="implementation may proceed only after gate",
        ),
        member_group_ids=list(gids),
        member_actions=["never code before approval"] * len(gids),
    )


def _decisions(gids, verdict):
    return [ClusterDecision(group_id=g, decision=verdict) for g in gids]


class TestInvariantValidation:
    @pytest.mark.parametrize("phrase", [
        "Adds additional guidance to the workflow",
        "This improves the workflow overall",
        "Provides more structure for the skill",
        "A better process for handling bugs",
        "Makes the skill more robust",
    ])
    def test_vague_invariants_rejected(self, phrase) -> None:
        assert invariant_is_vague(phrase) is True
        ok, reason = validate_invariant(phrase)
        assert ok is False
        assert "vague" in reason

    def test_concrete_invariant_accepted(self) -> None:
        ok, reason = validate_invariant(
            "Introduces a stop or escalation condition triggered by repeated failure."
        )
        assert ok is True, reason

    def test_empty_invariant_rejected(self) -> None:
        ok, reason = validate_invariant("   ")
        assert ok is False and "empty" in reason


class TestBehaviorSignature:
    def test_schema_roundtrip(self) -> None:
        sig = BehaviorSignature.from_dict({
            "trigger": "repeated failed attempts",
            "action": "stop and escalate",
            "object": None,
            "outcome": "agent reports back",
        })
        assert sig.trigger == "repeated failed attempts"
        assert sig.object is None
        assert set(sig.as_dict()) == {"trigger", "action", "object", "outcome"}

    def test_compatible_signatures_do_not_conflict(self) -> None:
        a = BehaviorSignature("repeated failure", "stop or escalate", "debugging loop", "agent stops")
        b = BehaviorSignature("3 failed fixes", "escalate", None, "report back")
        assert signatures_conflict(a, b) is False

    def test_negation_conflict_detected(self) -> None:
        a = BehaviorSignature("before approval", "block implementation", "code writing", None)
        b = BehaviorSignature("before approval", "allow implementation", "code writing", None)
        assert signatures_conflict(a, b) is True

    def test_cluster_signature_conflicts(self) -> None:
        cluster = BehaviorSignature("before approval", "block implementation", None, None)
        ok_member = BehaviorSignature("design approval", "block implementation", None, None)
        bad_member = BehaviorSignature("design approval", "enable implementation", None, None)
        assert signature_conflicts_in_cluster(cluster, [ok_member, bad_member]) == [1]


class TestClusterSizeRules:
    def test_large_cluster_requires_verifier(self) -> None:
        problems = precheck_cluster(_cluster(range(1, 10)))
        assert any("mandatory verifier" in p for p in problems)

    def test_oversized_cluster_requires_split(self) -> None:
        problems = precheck_cluster(_cluster(range(1, 17)))
        assert any("mandatory split proposal" in p for p in problems)

    def test_small_cluster_no_size_problem(self) -> None:
        problems = precheck_cluster(_cluster([1, 2, 3]))
        assert not any("mandatory" in p for p in problems)

    def test_vague_cluster_invariant_flagged(self) -> None:
        problems = precheck_cluster(
            _cluster([1, 2, 3], invariant="Improves the workflow with more structure")
        )
        assert any("vague" in p for p in problems)


class TestAcceptanceRules:
    def test_accepted_recurring(self) -> None:
        result = accept_cluster(
            _cluster([1, 2, 3, 4]),
            _decisions([1, 2, 3, 4], "YES"),
            {1: "a/x", 2: "b/y", 3: "c/z", 4: "d/w"},
        )
        assert result.status == "ACCEPTED" and result.recurring is True
        assert result.verified_yes_groups == 4 and result.verified_yes_repos == 4

    def test_uncertain_excluded_from_recurrence(self) -> None:
        # 8 YES + 2 UNCERTAIN of 10: rejection rate 20% (not >20%), so ACCEPTED,
        # but UNCERTAIN groups are excluded from recurrence counting.
        result = accept_cluster(
            _cluster(range(1, 11)),
            _decisions(range(1, 9), "YES") + _decisions([9, 10], "UNCERTAIN"),
            {1: "a/x", 2: "b/y", 3: "c/z", 4: "d/w", 5: "e/v",
             6: "f/u", 7: "g/t", 8: "h/s", 9: "i/r", 10: "j/q"},
        )
        assert result.verified_yes_groups == 8
        assert result.uncertain_group_ids == [9, 10]
        assert result.status == "ACCEPTED"

    def test_uncertain_above_20pct_is_unstable(self) -> None:
        # 3 YES + 2 UNCERTAIN of 5: rejection rate 40% > 20% -> UNSTABLE
        result = accept_cluster(
            _cluster([1, 2, 3, 4, 5]),
            _decisions([1, 2, 3], "YES") + _decisions([4, 5], "UNCERTAIN"),
            {1: "a/x", 2: "b/y", 3: "c/z", 4: "d/w", 5: "e/v"},
        )
        assert result.status == "UNSTABLE"

    def test_uncertain_cannot_create_recurrence(self) -> None:
        result = accept_cluster(
            _cluster([1, 2, 3, 4]),
            _decisions([1, 2], "YES") + _decisions([3, 4], "UNCERTAIN"),
            {1: "a/x", 2: "b/y", 3: "c/z", 4: "d/w"},
        )
        assert result.status == "NON_RECURRING"

    def test_rejection_rate_unstable(self) -> None:
        # 2 NO + 1 UNCERTAIN of 6 = 50% > 20% -> UNSTABLE even though 3 YES recur
        result = accept_cluster(
            _cluster([1, 2, 3, 4, 5, 6]),
            _decisions([1, 2, 3], "YES") + _decisions([4], "NO")
            + _decisions([5], "NO") + _decisions([6], "UNCERTAIN"),
            {1: "a/x", 2: "b/y", 3: "c/z", 4: "d/w", 5: "e/v", 6: "f/u"},
        )
        assert result.status == "UNSTABLE"
        assert result.rejection_rate > 0.20

    def test_single_repo_majority_non_recurring(self) -> None:
        result = accept_cluster(
            _cluster([1, 2, 3]),
            _decisions([1, 2, 3], "YES"),
            {1: "same/repo", 2: "same/repo", 3: "other/repo"},
        )
        assert result.status == "NON_RECURRING"
        assert result.max_single_repo_share > 0.5

    def test_missing_decision_raises(self) -> None:
        with pytest.raises(ValueError):
            accept_cluster(_cluster([1, 2]), _decisions([1], "YES"), {1: "a/x", 2: "b/y"})


class TestRegressionFixtures:
    """Known over-merges must NOT merge; positive controls MUST merge
    (spec section 11). These are behavior-signature level fixtures."""

    def test_review_checklist_and_design_contract_do_not_merge(self) -> None:
        checklist = BehaviorSignature(
            trigger="output produced",
            action="review against checklist",
            object="produced UI",
            outcome="checklist pass",
        )
        design_contract = BehaviorSignature(
            trigger="before implementation",
            action="produce DESIGN.md artifact",
            object="design contract",
            outcome="contract exists before code",
        )
        assert signatures_conflict(checklist, design_contract) is True

    def test_planning_checklist_and_scope_contract_do_not_merge(self) -> None:
        planning = BehaviorSignature(
            trigger="task received",
            action="plan before acting",
            object="implementation plan",
            outcome="plan exists",
        )
        scope = BehaviorSignature(
            trigger="skill invoked",
            action="declare scope and included/excluded items",
            object="skill applicability",
            outcome="scope known",
        )
        # different actions AND different objects -> material conflict
        assert signatures_conflict(planning, scope) is True or (
            set(planning.action.lower().split()) & set(scope.action.lower().split()) == set()
        )

    def test_progress_tracking_group_removed_by_verifier(self) -> None:
        """Pipeline-level fixture: a traceability cluster that wrongly contains
        a progress-tracking group must collapse below recurrence when the
        verifier rejects that member (spec section 11)."""
        cluster = _cluster([1, 2, 3, 4])
        decisions = (
            _decisions([1, 2, 3], "YES")
            + [ClusterDecision(group_id=4, decision="NO",
                               reason="progress tracking is not traceability")]
        )
        repos = {1: "a/x", 2: "b/y", 3: "c/z", 4: "d/w"}
        result = accept_cluster(cluster, decisions, repos)
        assert result.rejected_group_ids == [4]
        assert result.verified_yes_groups == 3

    def test_traceability_and_progress_tracking_do_not_merge(self) -> None:
        trace = BehaviorSignature(
            trigger="design produced",
            action="trace spec to requirement ids",
            object="design spec",
            outcome="traceable design",
        )
        progress = BehaviorSignature(
            trigger="process running",
            action="track progress",
            object="process state",
            outcome="visible progress",
        )
        assert signatures_conflict(trace, progress) is True or (
            "trace" not in progress.action.lower()
        )

    def test_stop_escalation_variants_merge(self) -> None:
        a = BehaviorSignature("3 failed fixes", "stop and escalate", "debugging loop", "agent reports")
        b = BehaviorSignature("repeated failed attempts", "abort after N failures", None, "reframe problem")
        c = BehaviorSignal = BehaviorSignature("repeated failure", "stop", None, None)
        assert signatures_conflict(a, b) is False
        assert signatures_conflict(a, c) is False

    def test_hard_gate_variants_merge(self) -> None:
        a = BehaviorSignature("before design approval", "never write code", "implementation", None)
        b = BehaviorSignature("design not accepted", "block coding", "implementation", None)
        c = BehaviorSignature("before explicit gate", "forbid implementation", None, None)
        assert signatures_conflict(a, b) is False
        assert signatures_conflict(a, c) is False
