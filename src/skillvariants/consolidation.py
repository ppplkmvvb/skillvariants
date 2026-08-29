"""Deterministic guardrails for semantic motif consolidation (guardrail v1).

The agent proposes canonical motif clusters; this module enforces the
structural rules BEFORE and AFTER model verification:

- vague-invariant rejection (section 7)
- behavior-signature schema + conflict detection (section 6)
- cluster-size rules (section 7)
- cluster acceptance rules with UNCERTAIN exclusion and the 20% rejection
  gate (section 9)

All functions are pure and testable; the verifier itself is an agent pass.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

VAGUE_INVARIANT_PATTERNS = (
    r"additional guidance",
    r"improv\w*\s+(the\s+)?workflow",
    r"more structure",
    r"better process",
    r"more robust",
    r"various improvements",
    r"general improvements",
)

SIGNATURE_FIELDS = ("trigger", "action", "object", "outcome")

# Behavior-verb families used for deterministic signature-conflict detection.
# Conflict = first verbs of two actions fall into DIFFERENT known families,
# or one is a gate/stop verb and the other is an allow verb.
VERB_FAMILIES = (
    ("gate_stop", {
        "stop", "abort", "escalate", "halt", "block", "prohibit", "forbid",
        "prevent", "lock", "gate", "refuse", "never",
    }),
    ("allow", {"allow", "enable", "permit", "implement", "write"}),
    ("produce", {"produce", "create", "generate", "add", "build"}),
    ("review", {"review", "check", "verify", "evaluate", "validate"}),
    ("track", {"track", "log", "record", "trace", "report"}),
    ("restructure", {"reorder", "restructure", "rename", "replace", "rebuild"}),
    ("delegate", {"route", "delegate", "handoff", "hand-off"}),
    ("announce", {"announce", "declare", "state"}),
    ("translate", {"translate"}),
)

_NEGATION_RE = re.compile(r"\b(never|no|without|not)\b", re.I)


def _first_verb(action: str) -> str | None:
    for token in re.findall(r"[a-z]+", action.lower()):
        if token in ("do", "not", "never", "always", "before", "after", "the", "a", "an"):
            if token in ("never",):
                return "never"
            continue
        if token in {verb for _, verbs in VERB_FAMILIES for verb in verbs}:
            return token
        return token  # unknown first verb
    return None


def _verb_family(action: str) -> str | None:
    verb = _first_verb(action)
    if verb is None:
        return None
    if verb == "never" or _NEGATION_RE.search(action.lower()):
        return "gate_stop"
    for name, verbs in VERB_FAMILIES:
        if verb in verbs:
            return name
    return None


@dataclass
class BehaviorSignature:
    trigger: str | None
    action: str | None
    object: str | None
    outcome: str | None

    @classmethod
    def from_dict(cls, data: dict) -> "BehaviorSignature":
        return cls(
            trigger=_clean(data.get("trigger")),
            action=_clean(data.get("action")),
            object=_clean(data.get("object")),
            outcome=_clean(data.get("outcome")),
        )

    def as_dict(self) -> dict:
        return {
            "trigger": self.trigger,
            "action": self.action,
            "object": self.object,
            "outcome": self.outcome,
        }


@dataclass
class ProposedCluster:
    label: str
    invariant: str
    signature: BehaviorSignature
    member_group_ids: list[int]
    member_actions: list[str] = field(default_factory=list)


@dataclass
class ClusterDecision:
    """Agent verifier verdict for one supporting group."""

    group_id: int
    decision: str  # YES | NO | UNCERTAIN
    reason: str = ""
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.decision not in ("YES", "NO", "UNCERTAIN"):
            raise ValueError(f"invalid verifier decision: {self.decision!r}")


@dataclass
class AcceptResult:
    accepted: bool
    recurring: bool
    rejection_rate: float
    verified_yes_groups: int
    verified_yes_repos: int
    max_single_repo_share: float
    uncertain_group_ids: list[int]
    rejected_group_ids: list[int]
    status: str  # ACCEPTED | UNSTABLE | NON_RECURRING


def _clean(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def invariant_is_vague(invariant: str) -> bool:
    lowered = invariant.lower()
    return any(re.search(pattern, lowered) for pattern in VAGUE_INVARIANT_PATTERNS)


def validate_invariant(invariant: str) -> tuple[bool, str]:
    if not invariant or not invariant.strip():
        return False, "empty invariant"
    if invariant_is_vague(invariant):
        return False, "vague invariant"
    if len(invariant.strip()) < 20:
        return False, "invariant too short to be a behavioral claim"
    return True, ""


def signatures_conflict(
    left: BehaviorSignature, right: BehaviorSignature
) -> bool:
    """Material conflict when the two actions belong to different known
    behavior-verb families (e.g. gate vs allow, review vs produce). Actions
    with unknown verbs are not judged here — the verifier handles them.
    Pure topic similarity is never a conflict at this layer."""
    if not (left.action and right.action):
        return False
    left_family = _verb_family(left.action)
    right_family = _verb_family(right.action)
    if left_family and right_family:
        return left_family != right_family
    return False


def _objects_overlap(a: str, b: str) -> bool:
    a_words = {w for w in re.findall(r"[a-z]+", a.lower()) if len(w) > 2}
    b_words = {w for w in re.findall(r"[a-z]+", b.lower()) if len(w) > 2}
    return bool(a_words & b_words)


_NEGATION = re.compile(r"\b(no|never|without| prohibit|forbid|block|prevent)\b", re.I)


def _terms_overlap(a: str, b: str) -> bool:
    a_words = {w for w in re.findall(r"[a-z]+", a.lower()) if len(w) > 2}
    b_words = {w for w in re.findall(r"[a-z]+", b.lower()) if len(w) > 2}
    if not a_words or not b_words:
        return True  # cannot judge; do not flag
    if a_words & b_words:
        return True
    return False


def precheck_cluster(proposed: ProposedCluster) -> list[str]:
    """Deterministic pre-checks before the model verifier (section 7)."""
    problems: list[str] = []
    ok, reason = validate_invariant(proposed.invariant)
    if not ok:
        problems.append(f"invariant: {reason}")
    if not proposed.member_actions or any(
        not action.strip() for action in proposed.member_actions
    ):
        problems.append("empty member action")
    if len(proposed.member_group_ids) > 15:
        problems.append(
            f"cluster size {len(proposed.member_group_ids)} > 15: mandatory split proposal"
        )
    elif len(proposed.member_group_ids) > 8:
        problems.append(
            f"cluster size {len(proposed.member_group_ids)} > 8: mandatory verifier"
        )
    return problems


def signature_conflicts_in_cluster(
    signature: BehaviorSignature, member_signatures: list[BehaviorSignature]
) -> list[int]:
    """Indexes of member signatures that materially conflict with the cluster."""
    return [
        index
        for index, member in enumerate(member_signatures)
        if signatures_conflict(signature, member)
    ]


def accept_cluster(
    proposed: ProposedCluster,
    decisions: list[ClusterDecision],
    group_repos: dict[int, str],
) -> AcceptResult:
    """Cluster acceptance rules (section 9). Deterministic.

    UNCERTAIN groups are excluded from recurrence. Rejection rate
    (NO + UNCERTAIN) / proposed > 20% marks the cluster UNSTABLE.
    """
    by_group = {d.group_id: d for d in decisions}
    missing = [gid for gid in proposed.member_group_ids if gid not in by_group]
    if missing:
        raise ValueError(f"missing verifier decisions for groups: {missing}")

    yes_ids = [gid for gid in proposed.member_group_ids
               if by_group[gid].decision == "YES"]
    uncertain_ids = [gid for gid in proposed.member_group_ids
                     if by_group[gid].decision == "UNCERTAIN"]
    rejected_ids = [gid for gid in proposed.member_group_ids
                    if by_group[gid].decision == "NO"]

    n_proposed = len(proposed.member_group_ids)
    rejection_rate = (len(rejected_ids) + len(uncertain_ids)) / n_proposed

    repo_counts: Counter = Counter()
    for gid in yes_ids:
        repo = group_repos.get(gid)
        if repo:
            repo_counts[repo] += 1
    yes_repos = len(repo_counts)
    max_share = (max(repo_counts.values()) / len(yes_ids)) if yes_ids else 0.0

    recurring = len(yes_ids) >= 3 and yes_repos >= 3 and max_share <= 0.5
    unstable = rejection_rate > 0.20

    if not recurring:
        status = "NON_RECURRING"
    elif unstable:
        status = "UNSTABLE"
    else:
        status = "ACCEPTED"

    return AcceptResult(
        accepted=status == "ACCEPTED",
        recurring=recurring and not unstable,
        rejection_rate=round(rejection_rate, 3),
        verified_yes_groups=len(yes_ids),
        verified_yes_repos=yes_repos,
        max_single_repo_share=round(max_share, 3),
        uncertain_group_ids=uncertain_ids,
        rejected_group_ids=rejected_ids,
        status=status,
    )


from collections import Counter  # noqa: E402  (kept late to mirror usage)
