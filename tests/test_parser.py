"""Unit tests for URL parsing and SKILL.md frontmatter/body parsing."""
from __future__ import annotations

import pytest

from skillvariants.parser import (
    GitHubRef,
    parse_github_url,
    parse_skill_md,
    split_frontmatter,
)


class TestParseGitHubUrl:
    def test_blob_url(self) -> None:
        ref = parse_github_url(
            "https://github.com/obra/superpowers/blob/main/"
            "skills/systematic-debugging/SKILL.md"
        )
        assert ref == GitHubRef("obra", "superpowers", "main",
                                "skills/systematic-debugging/SKILL.md")

    def test_blob_url_with_query(self) -> None:
        ref = parse_github_url(
            "https://github.com/anthropics/skills/blob/main/"
            "skills/frontend-design/SKILL.md?plain=1"
        )
        assert ref.repo_slug == "anthropics/skills"
        assert ref.path == "skills/frontend-design/SKILL.md"

    def test_raw_url(self) -> None:
        ref = parse_github_url(
            "https://github.com/anthropics/skills/raw/main/"
            "skills/frontend-design/SKILL.md"
        )
        assert ref.ref == "main"

    def test_rawgithubusercontent_url(self) -> None:
        ref = parse_github_url(
            "https://raw.githubusercontent.com/obra/superpowers/"
            "main/skills/brainstorming/SKILL.md"
        )
        assert ref.owner == "obra"
        assert ref.path == "skills/brainstorming/SKILL.md"

    def test_invalid_url(self) -> None:
        with pytest.raises(ValueError):
            parse_github_url("https://github.com/obra/superpowers")
        with pytest.raises(ValueError):
            parse_github_url("ftp://example.com/x")

    def test_ref_properties(self) -> None:
        ref = GitHubRef("a", "b", "main", "c/SKILL.md")
        assert ref.raw_url.endswith("raw.githubusercontent.com/a/b/main/c/SKILL.md")
        assert "repos/a/b/" in ref.api_contents_url


class TestSplitFrontmatter:
    def test_valid_frontmatter(self) -> None:
        text = '---\nname: my-skill\ndescription: Does things\n---\n# Hello\n'
        fm, body, had, errors = split_frontmatter(text)
        assert had is True
        assert fm == {"name": "my-skill", "description": "Does things"}
        assert body == "# Hello"
        assert errors == []

    def test_missing_frontmatter(self) -> None:
        text = "# No frontmatter here\n"
        fm, body, had, errors = split_frontmatter(text)
        assert had is False
        assert fm == {}
        assert body == text
        assert errors == []

    def test_unterminated_frontmatter(self) -> None:
        text = "---\nname: broken\n"
        fm, body, had, errors = split_frontmatter(text)
        assert fm == {}
        assert errors and "unterminated" in errors[0]

    def test_yaml_error_recorded(self) -> None:
        text = "---\nname: [unclosed\n---\nbody\n"
        _fm, _body, had, errors = split_frontmatter(text)
        assert had is True
        assert errors

    def test_extra_frontmatter_fields_preserved(self) -> None:
        text = (
            "---\nname: x\nlicense: MIT\ncanonical_skill: ../real/SKILL.md\n"
            "custom: value\n---\nbody\n"
        )
        fm, _body, _had, errors = split_frontmatter(text)
        assert errors == []
        assert fm["license"] == "MIT"
        assert fm["custom"] == "value"

    def test_canonical_ref_extraction(self) -> None:
        text = "---\nname: x\ntext_scope: reference\ncanonical_skill: ../../real/SKILL.md\n---\nbody\n"
        doc = parse_skill_md(text)
        assert doc.canonical_ref == "../../real/SKILL.md"


class TestParseSkillMd:
    def test_doc_accessors(self) -> None:
        doc = parse_skill_md("---\nname: x\n---\n# X\n")
        assert doc.name == "x"
        assert doc.description is None
        assert doc.raw.startswith("---")

    def test_bom_stripped(self) -> None:
        doc = parse_skill_md("\ufeff---\nname: x\n---\nB\n")
        assert doc.name == "x"
