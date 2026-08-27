"""v0.1 production tests: placeholder detection, package metadata, JSON contract."""
from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from skillvariants.features import extract_features
from skillvariants.parser import parse_skill_md
from skillvariants.ranking import representative_score

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# --- placeholder / template detection (spec section 7) ----------------------

def _feat(body_text: str):
    doc = parse_skill_md(f"---\nname: t\n---\n{body_text}")
    return extract_features(doc)


class TestPlaceholderDetection:
    def test_template_skeleton_scores_high(self) -> None:
        skeleton = (
            "# Skill\n## When to Use\n- [Describe trigger scenarios]\n"
            "## Instructions\n[Add step-by-step instructions]\n"
            "## Output\n[Insert output format here]\n"
            "TODO: fill everything\nYOUR_API_KEY here\nREPLACE_ME\n"
        )
        feats = _feat(skeleton)
        assert feats.n_placeholder_hits >= 6
        assert feats.placeholder_signal >= 0.5

    def test_honest_rewrite_scores_zero(self) -> None:
        honest = (
            "# Skill\nDo the work carefully.\n## Steps\n"
            "1. Read the failing output.\n2. Reproduce it locally.\n"
            "3. Fix and verify with a test.\n" * 3
        )
        feats = _feat(honest)
        assert feats.n_placeholder_hits == 0
        assert feats.placeholder_signal == 0.0

    def test_placeholder_heavy_document_penalized_but_ranked(self) -> None:
        from tests_helpers import build_test_pool, doc_text, TARGET_BODY

        near_copy = doc_text(TARGET_BODY.replace("Run git commands", "Run git cli"))
        honest_compact = doc_text(
            "# Sample\nShort loop: investigate, reproduce, fix, verify.\n"
            "Stop after three failed hypotheses.\n## Loop\n1. read error\n2. fix\n"
        )
        template = doc_text(
            "# Sample\n- [Describe trigger scenarios]\n[Add step-by-step "
            "instructions]\nTODO: complete the workflow\nTBD details\n"
            "[Insert verification checklist]\n"
        )
        pool = build_test_pool({
            ("clone/repo", "a/SKILL.md"): near_copy,
            ("honest/repo", "c/SKILL.md"): honest_compact,
            ("template/repo", "t/SKILL.md"): template,
        })
        rows = {r.repo: r for r in pool["pool"]}
        t_row, h_row = rows["template/repo"], rows["honest/repo"]
        # penalty applies...
        assert t_row.feats.placeholder_signal > h_row.feats.placeholder_signal
        s_t = representative_score(t_row, "compact-rewrite")
        s_h = representative_score(h_row, "compact-rewrite")
        raw_t = representative_score.__wrapped__(t_row, "compact-rewrite") if hasattr(
            representative_score, "__wrapped__") else None
        # ...and honest rewrite outranks the template within the archetype
        assert s_h > s_t

    def test_penalty_does_not_exclude_discovery(self) -> None:
        """The document must still be discovered/related — only ranked lower."""
        from tests_helpers import build_test_pool, doc_text, TARGET_BODY

        near_copy = doc_text(TARGET_BODY.replace("Run git commands", "Run git cli"))
        template = doc_text(
            "# Sample\n- [Describe trigger scenarios]\n[Add step-by-step "
            "instructions]\nTODO: complete the workflow\nTBD details\n"
            "[Insert verification checklist]\n"
        )
        pool = build_test_pool({
            ("clone/repo", "a/SKILL.md"): near_copy,
            ("template/repo", "t/SKILL.md"): template,
        })
        rows = {r.repo: r for r in pool["pool"]}
        assert rows["template/repo"].relatedness >= 0.33 or (
            rows["template/repo"].sim.name_match
        )


# --- packaging metadata (spec section 25/26) ---------------------------------

class TestPackageMetadata:
    def _pyproject(self) -> dict:
        data = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text("utf-8"))
        return data["project"]

    def test_name_version_and_script(self) -> None:
        project = self._pyproject()
        assert project["name"] == "skillvariants"
        assert project["version"] == "0.1.1"
        assert project["scripts"] == {"skillvariants": "skillvariants.cli:app"}

    def test_license_python_and_keywords(self) -> None:
        project = self._pyproject()
        assert "Apache" in project["license"]["text"]
        assert project["requires-python"] == ">=3.11"
        for keyword in ("agent-skills", "claude-code", "skill-md"):
            assert keyword in project["keywords"]


# --- JSON contract preservation ----------------------------------------------

class TestJsonContract:
    def test_mutations_payload_validates_with_json_loads(self, capsys) -> None:
        from skillvariants.cli import emit_json
        payload = {
            "skill": {"name": "demo"},
            "exact_copy_count": 3,
            "unique_related_variants": 7,
            "archetypes": [
                {
                    "type": "compact-rewrite",
                    "group_count": 1,
                    "representatives": [{
                        "repository": "a/b",
                        "sha256_full": "f" * 64,
                        "signals": ["length decreased by 50%"],
                    }],
                }
            ],
        }
        emit_json(payload)
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["exact_copy_count"] == 3
        assert len(parsed["archetypes"]) == 1
        assert re.fullmatch(r"[0-9a-f]{64}", parsed["archetypes"][0]
                            ["representatives"][0]["sha256_full"])
