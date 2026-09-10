"""Production evidence assembly, independent of CLI process state."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from urllib.parse import quote

from .classify import classify_pair
from .comparison import EVIDENCE_POLICY, compare_documents, source_identity
from .features import extract_features
from .github import GitHubClient, GitHubError
from .parser import parse_github_url, parse_skill_md
from .ranking import MIN_RELATEDNESS, build_variant_row
from .similarity import normalize_for_hash, score_similarity, sha256

DEFAULT_MAX_PAGES = 3


def _fetch_document(client, ref):
    if hasattr(client, 'fetch_document'):
        return client.fetch_document(ref)
    return parse_skill_md(client.fetch_text(ref), source=ref)


def _direct_url(ref):
    return (f'https://github.com/{ref.repo_slug}/blob/'
            f'{quote(ref.ref, safe="")}/{quote(ref.path, safe="/")}')


def _changed_excerpt(comparison, side):
    """Short display summary only; source evidence lives in complete paired hunks."""
    texts = []
    for hunk in comparison['hunks']:
        for change in hunk['changes']:
            if change['tag'] == 'equal':
                continue
            start = change[f'{side}_start_line']
            stop = start + change[f'{side}_line_count']
            texts.extend(line['text'].strip() for line in hunk[side]['lines']
                         if start <= line['line_number'] < stop and line['text'].strip())
    return ' | '.join(texts[:3])[:900]


def build_evidence_payload(
    url: str, cache_dir: Path | None = None, max_pages: int = DEFAULT_MAX_PAGES,
    evidence_builder=None, fetch_errors_out: list | None = None,
    *, github_options: dict | None = None,
) -> dict:
    """Version 2 evidence: each group retains one distinct normalized candidate.

    Fuzzy browsing neighborhoods cannot establish behavioral equivalence, so
    semantic study groups never hide distinct candidates behind a representative.
    The previous scalar fields remain; counts now have explicit denominators.
    """
    if evidence_builder is not None:
        return evidence_builder(url)
    cache_dir = Path(cache_dir) if cache_dir is not None else Path('.cache/skillvariants')
    client = GitHubClient(cache_dir=cache_dir, **(github_options or {}))
    requested_ref = parse_github_url(url)
    target = _fetch_document(client, requested_ref)
    target_ref = target.source or requested_ref
    target_feats = extract_features(target)
    name = target.name
    if not name:
        raise ValueError('target has no frontmatter name; cannot search')
    query = f'"name: {name}" filename:SKILL.md'
    hits = client.code_search(query, max_pages=max_pages)

    seen, candidates = set(), []
    for hit in hits:
        key = (hit.repo, hit.path)
        if key in seen or not hit.repo:
            continue
        seen.add(key)
        if key == (target_ref.repo_slug, target_ref.path):
            continue
        candidates.append(hit)

    target_hash = sha256(normalize_for_hash(target.raw))
    fetch_errors, fetched, exact_copies, by_hash = [], 0, 0, {}
    for hit in candidates:
        try:
            cdoc = _fetch_document(client, hit.to_ref())
        except GitHubError as exc:
            fetch_errors.append(f'{hit.repo}/{hit.path}: {exc}')
            continue
        fetched += 1
        full_hash = sha256(normalize_for_hash(cdoc.raw))
        exact_copies += int(full_hash == target_hash)
        occurrence = source_identity(cdoc)
        occurrence['normalized_hash'] = full_hash
        occurrence['direct_skill_url'] = _direct_url(cdoc.source or hit.to_ref())
        if full_hash in by_hash:
            by_hash[full_hash]['occurrences'].append(occurrence)
            continue
        feats = extract_features(cdoc)
        sim = score_similarity(target, target_feats, cdoc, feats)
        resolved = cdoc.source or hit.to_ref()
        row = build_variant_row(
            repo=resolved.repo_slug, path=resolved.path, ref=resolved.ref,
            doc=cdoc, feats=feats, sim=sim,
            classification=classify_pair(target, target_feats, cdoc, feats, sim),
            sha256_full=full_hash, target_doc=target, target_feats=target_feats,
            target_name=name,
        )
        by_hash[full_hash] = {'row': row, 'occurrences': [occurrence]}

    pool = sorted((item['row'] for item in by_hash.values()), key=lambda r: r.sim.score, reverse=True)
    gated = [row for row in pool if row.relatedness >= MIN_RELATEDNESS]
    group_rows = []
    for gid, rep in enumerate(gated, start=1):
        occurrences = by_hash[rep.sha256_full]['occurrences']
        mf = rep.mutation_features
        comparison = compare_documents(target, rep.doc)
        group_rows.append({
            'group_id': gid,
            'repository': rep.repo, 'path': rep.path, 'ref': rep.ref,
            'direct_skill_url': _direct_url(rep.doc.source),
            'archetype': rep.classification.primary,
            'relatedness': round(rep.relatedness, 3),
            'member_count': 1, 'occurrence_count': len(occurrences),
            'normalized_hash': rep.sha256_full,
            'occurrences': occurrences,
            'comparison': comparison,
            'structural_signals': {
                'length_delta': round(mf.length_delta_ratio, 3),
                'headings_added': mf.headings_added_count,
                'headings_removed': mf.headings_removed_count,
                'commands_added': mf.command_set_added,
                'commands_removed': mf.command_set_removed,
                'cross_skill_ref_delta': mf.cross_skill_ref_delta,
                'routing_signals': rep.feats.routing_signals[:6],
                'wrapper_signals': rep.feats.wrapper_signals[:6],
                'workflow_structure_delta': round(mf.workflow_structure_delta, 3),
                'placeholder_signal': round(rep.feats.placeholder_signal, 3),
            },
            'added_excerpt': _changed_excerpt(comparison, 'b'),
            'removed_excerpt': _changed_excerpt(comparison, 'a'),
            'excerpt_is_summary': True,
        })
    if fetch_errors_out is not None:
        fetch_errors_out.extend(fetch_errors)
    return {
        'schema_version': '2',
        'target': {
            'repository': target_ref.repo_slug, 'path': target_ref.path, 'ref': target_ref.ref,
            'direct_skill_url': _direct_url(target_ref), 'name': name,
            'normalized_hash': target_hash, 'source': source_identity(target),
        },
        'summary': {
            'candidate_count': len(candidates), 'fetched_count': fetched,
            'fetch_error_count': len(fetch_errors), 'unique_variant_count': len(pool),
            'related_variant_count': len(gated), 'gated_out_count': len(pool) - len(gated),
            'exact_copy_count': exact_copies, 'mutation_group_count': len(group_rows),
            'related_occurrence_count': sum(g['occurrence_count'] for g in group_rows),
            'broad_archetype_counts': dict(Counter(g['archetype'] for g in group_rows)),
        },
        'count_definitions': {
            'candidate_count': 'Unique repository/path search hits, excluding the target.',
            'fetched_count': 'Successfully fetched candidate occurrences before content deduplication.',
            'unique_variant_count': 'Distinct normalized candidate contents before the relatedness gate.',
            'related_variant_count': 'Distinct normalized candidate contents passing the relatedness gate.',
            'exact_copy_count': 'Fetched occurrences matching target normalized content; not independent adoption.',
            'mutation_group_count': 'One evidence group per related distinct normalized candidate, including exact copies.',
        },
        'search': {'query': query, 'max_pages': max_pages,
                   'cache': getattr(client, 'search_metadata', {}),
                   'coverage': 'Bounded GitHub code search; not an exhaustive repository census.'},
        'evidence_policy': EVIDENCE_POLICY,
        'fetch_errors': fetch_errors,
        'groups': group_rows,
    }
