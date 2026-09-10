"""Textual proximity must not erase changed instructions before review."""
from skillvariants.classify import classify_pair
from skillvariants.features import extract_features
from skillvariants.parser import parse_skill_md
from skillvariants.ranking import build_variant_row, group_variants
from skillvariants.similarity import score_similarity


def document(body):
    return parse_skill_md("---\nname: approval\ndescription: Review a proposed action.\n---\n# Review\n" + body)


def row(target, candidate, repo):
    tf, cf = extract_features(target), extract_features(candidate)
    sim = score_similarity(target, tf, candidate, cf)
    return build_variant_row(
        repo=repo, path="SKILL.md", ref="main", doc=candidate, feats=cf,
        sim=sim, classification=classify_pair(target, tf, candidate, cf, sim),
        copy_count=1, sha256_full=repo, target_doc=target, target_feats=tf,
        target_name="approval",
    )


def test_same_length_opposite_instruction_is_not_a_perfect_match():
    target = document("Wait for approval. Never act before approval.")
    changed = document("Never wait for approval. Act before approval.")
    result = row(target, changed, "example/reversal")
    assert result.sim.char_ratio < 1.0
    assert result.sim.score < 1.0
    assert result.magnitude > 0.0


def test_same_structure_textual_rewrite_is_not_hidden_in_copy_hub():
    target = document("Wait for approval. Never act before approval.")
    changed = document("Never wait for approval. Act before approval.")
    groups = group_variants([
        row(target, target, "example/original"),
        row(target, changed, "example/reversal"),
    ])
    assert len(groups) == 2


def test_same_length_unrelated_bodies_have_lower_character_similarity():
    target = document("abcdefg")
    changed = document("hijklmn")
    assert row(target, changed, "example/other").sim.char_ratio < 1.0


def test_identical_headingless_content_has_no_structural_mutation():
    target = parse_skill_md("---\nname: approval\n---\nWait for approval.")
    result = row(target, target, "example/identical")
    assert result.sim.score == 1.0
    assert result.magnitude == 0.0
