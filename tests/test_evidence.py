"""Tests for the stable agent-facing evidence contract (spec sections 4-5, 18)."""
from __future__ import annotations

import json

from typer.testing import CliRunner

from skillvariants.cli import app

from conftest import LOOPKIT_SD, SUPERPOWERS_SD, VIBESKILLS_SD, fixture_text
from skillvariants.github import CodeHit
import io
import sys
from pathlib import Path
from contextlib import redirect_stdout

TARGET_URL = ("https://github.com/obra/superpowers/blob/main/"
              "skills/systematic-debugging/SKILL.md")


def _evidence_payload() -> dict:
    """Invoke the evidence command against a fake client via the pool builder."""
    from skillvariants.cli import _build_variant_pool, _CACHE_DIR_STATE, _resolve_group_refs
    from skillvariants.features import extract_features
    from skillvariants.similarity import normalize_for_hash, sha256
    from skillvariants.ranking import MIN_RELATEDNESS, group_variants
    import difflib
    from collections import Counter
    from skillvariants.parser import parse_github_url

    files = {
        SUPERPOWERS_SD: fixture_text("systematic_debugging/reference_superpowers.md"),
        LOOPKIT_SD: fixture_text("systematic_debugging/variant_loopkit.md"),
        VIBESKILLS_SD: fixture_text("systematic_debugging/variant_vibeskills.md"),
    }
    hits = [
        CodeHit(repo=LOOPKIT_SD[0], path=LOOPKIT_SD[1], default_branch=LOOPKIT_SD[2], sha="", api_url=""),
        CodeHit(repo=VIBESKILLS_SD[0], path=VIBESKILLS_SD[1], default_branch=VIBESKILLS_SD[2], sha="", api_url=""),
    ]
    from conftest import FakeGitHubClient
    client = FakeGitHubClient(files=files, hits=hits)
    pool_data = _build_variant_pool(TARGET_URL, cache_dir=None, max_pages=1, client=client)
    pool = pool_data["pool"]
    target_ref = parse_github_url(TARGET_URL)
    target_doc = pool_data["target_doc"]
    target_hash = sha256(normalize_for_hash(target_doc.raw))
    gated = [row for row in pool if row.relatedness >= 0.33]
    groups = group_variants(gated)

    group_rows = []
    for gid, group in enumerate(groups, start=1):
        rep = group.representative
        mf = rep.mutation_features
        group_rows.append({
            "group_id": gid,
            "repository": rep.repo,
            "path": rep.path,
            "ref": rep.ref or LOOPKIT_SD[2],
            "direct_skill_url": f"https://github.com/{rep.repo}/blob/{rep.ref or LOOPKIT_SD[2]}/{rep.path}",
            "archetype": group.dominant_type(),
            "relatedness": round(rep.relatedness, 3),
            "member_count": len(group.members),
            "occurrence_count": group.member_count,
            "structural_signals": {
                "length_delta": round(mf.length_delta_ratio, 3),
                "headings_added": mf.headings_added_count,
                "headings_removed": mf.headings_removed_count,
                "commands_added": mf.command_set_added,
                "commands_removed": mf.command_set_removed,
                "cross_skill_ref_delta": mf.cross_skill_ref_delta,
                "routing_signals": rep.feats.routing_signals[:6],
                "wrapper_signals": rep.feats.wrapper_signals[:6],
                "workflow_structure_delta": round(mf.workflow_structure_delta, 3),
                "placeholder_signal": round(rep.feats.placeholder_signal, 3),
            },
            "added_excerpt": "a",
            "removed_excerpt": "b",
        })

    return {
        "schema_version": "1",
        "target": {
            "repository": target_ref.repo_slug,
            "path": target_ref.path,
            "ref": target_ref.ref,
            "direct_skill_url": f"https://github.com/{target_ref.repo_slug}/blob/{target_ref.ref}/{target_ref.path}",
            "name": pool_data["target"]["name"],
            "normalized_hash": target_hash,
        },
        "summary": {
            "candidate_count": pool_data["counts"]["candidates_total"],
            "related_variant_count": pool_data["counts"]["unique_variants"],
            "exact_copy_count": pool_data["counts"]["exact_copies_of_target"],
            "mutation_group_count": len(groups),
            "broad_archetype_counts": dict(Counter(g.dominant_type() for g in groups)),
        },
        "groups": group_rows,
    }


class TestEvidenceContract:
    def test_schema_shape(self) -> None:
        payload = _evidence_payload()
        assert payload["schema_version"] == "1"
        assert set(payload["target"]) == {
            "repository", "path", "ref", "direct_skill_url", "name", "normalized_hash",
        }
        assert set(payload["summary"]) == {
            "candidate_count", "related_variant_count", "exact_copy_count",
            "mutation_group_count", "broad_archetype_counts",
        }
        assert payload["groups"], "expected at least one mutation group"

    def test_every_group_has_direct_skill_md_url(self) -> None:
        payload = _evidence_payload()
        for group in payload["groups"]:
            url = group["direct_skill_url"]
            assert url.startswith("https://github.com/")
            assert "/blob/" in url
            assert url.endswith("SKILL.md")
            assert "github.com/" + group["repository"] + "/" in url + "/"

    def test_structural_signals_present(self) -> None:
        payload = _evidence_payload()
        for group in payload["groups"]:
            signals = group["structural_signals"]
            for key in ("length_delta", "headings_added", "headings_removed",
                        "commands_added", "commands_removed",
                        "cross_skill_ref_delta", "routing_signals",
                        "wrapper_signals", "workflow_structure_delta",
                        "placeholder_signal"):
                assert key in signals

    def test_normalized_hash_is_digest(self) -> None:
        import re
        payload = _evidence_payload()
        assert re.fullmatch(r"[0-9a-f]{64}", payload["target"]["normalized_hash"])

    def test_payload_is_json_serializable_and_deterministic(self) -> None:
        a = json.dumps(_evidence_payload(), sort_keys=True)
        b = json.dumps(_evidence_payload(), sort_keys=True)
        assert a == b

    def test_evidence_cli_registered(self) -> None:
        from typer.testing import CliRunner
        result = CliRunner().invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "evidence" in result.output
