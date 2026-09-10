"""Paired raw-line evidence has bounded output and explicit omissions."""
import hashlib
import json

from skillvariants.parser import parse_skill_md


def compare(a, b, **kwargs):
    import skillvariants
    import importlib.util
    assert importlib.util.find_spec("skillvariants.comparison") is not None, "shared production comparison is missing"
    from skillvariants.comparison import compare_documents
    return compare_documents(parse_skill_md(a), parse_skill_md(b), **kwargs)


def test_paired_hunks_include_raw_line_numbers_and_frontmatter():
    a = "---\nname: sample\nmode: manual\n---\nAsk approval before deploy.\n"
    b = a.replace("manual", "auto").replace("Ask approval", "Do not ask approval")
    result = compare(a, b)
    hunk = result["hunks"][0]
    assert hunk["hunk_id"] == "hunk-001"
    assert {"line_number": 5, "text": "Ask approval before deploy."} in hunk["a"]["lines"]
    assert {"line_number": 5, "text": "Do not ask approval before deploy."} in hunk["b"]["lines"]
    assert "-mode: manual" in result["unified_diff"]
    assert result["sources"]["a"]["raw_sha256"] == hashlib.sha256(a.encode()).hexdigest()
    assert result["truncation"]["truncated"] is False
    json.dumps(result)


def test_truncation_never_presents_partial_hunk_as_complete_evidence():
    a = "\n".join(f"before {i}" for i in range(1000))
    b = "\n".join(f"after {i}" for i in range(1000))
    result = compare(a, b, max_lines=40, max_diff_chars=200)
    assert result["truncation"]["truncated"]
    assert result["truncation"]["omitted_lines"] > 0
    assert len(result["unified_diff"]) <= 200
    assert sum(len(h[s]["lines"]) for h in result["hunks"] for s in ("a", "b")) <= 40
    assert "absence" in result["evidence_policy"]


def test_identical_content_has_no_invented_changes():
    result = compare("same\n", "same\n")
    assert result["hunks"] == [] and result["unified_diff"] == ""
    assert not result["truncation"]["truncated"]


def test_newline_only_changes_are_visible_even_without_text_hunks():
    result = compare("same\r\n", "same\n")
    assert result.get('raw_equal') is False
    assert result['line_text_equal'] is True
    assert result['formatting_changes']
