"""Regression tests pinning the first-spike bug fixes (spec section 27)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from skillvariants.cli import emit_json
from skillvariants.classify import classify_pair, mutation_summary
from skillvariants.features import extract_features
from skillvariants.parser import parse_skill_md
from skillvariants.similarity import score_similarity


def test_emit_json_output_is_parseable_and_markup_free(capsys) -> None:
    payload = {"nested": {"text": "word " * 80, "list": [1, 2, {"k": "v"}]}}
    emit_json(payload)
    out = capsys.readouterr().out
    data = json.loads(out)  # must be valid machine-readable JSON
    assert "word" in data["nested"]["text"]
    assert "\x1b[" not in out  # no Rich/ANSI escape sequences leak into JSON


def test_negative_length_delta_renders_with_minus_sign() -> None:
    target = parse_skill_md("---\nname: t\n---\n" + ("line of body text\n" * 100))
    shorter = parse_skill_md("---\nname: t\n---\nshort body\n")
    tf = extract_features(target)
    cf = extract_features(shorter)
    sim = score_similarity(target, tf, shorter, cf)
    cls = classify_pair(target, tf, shorter, cf, sim)
    summary = mutation_summary(target, tf, shorter, cf, sim, cls)
    assert summary["length_change"].startswith("-"), summary["length_change"]


def test_qqmusic_api_urls_use_next_branch() -> None:
    """Regression: Rain120/qq-music-api's default branch is `next`, so any
    bundled URL referencing that repo must use it (`main` 404s)."""
    from tests_helpers import LIVE_VARIANT_URLS

    assert "qq-music-api/blob/next/" in LIVE_VARIANT_URLS["frontend-design"]
    assert "qq-music-api/blob/main" not in json.dumps(LIVE_VARIANT_URLS)


def test_sha256_helper_produces_64char_hex() -> None:
    from skillvariants.similarity import sha256

    digest = sha256("anything")
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
