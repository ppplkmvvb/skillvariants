"""Evaluate supplied predictions on authored synthetic cases; no model is called."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TASK_LABELS = {
    'change_direction': ('ADDED', 'REMOVED', 'MODIFIED', 'UNCHANGED', 'ABSTAIN'),
    'citation_integrity': ('VALID', 'INVALID', 'ABSTAIN'),
    'task_coverage': ('COMPLETE', 'INCOMPLETE', 'ABSTAIN'),
}
LIMITATIONS = (
    'Small author-labeled synthetic cases are not a representative sample of real Skills. '
    'Self-tests or oracle replay are not independent model accuracy evidence. '
    'A declared blind run is a procedural assertion, not verified by this scorer. '
    'Quote integrity does not establish semantic entailment or independent adoption.'
)


def read_json_strict(path: Path) -> dict:
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'duplicate JSON key: {key!r}')
            result[key] = value
        return result
    def reject_constant(value):
        raise ValueError(f'non-JSON numeric constant: {value}')
    result = json.loads(Path(path).read_text(encoding='utf-8-sig'),
                        object_pairs_hook=unique_object, parse_constant=reject_constant)
    if not isinstance(result, dict):
        raise ValueError('JSON document must be an object')
    return result


def canonical_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                      separators=(',', ':')).encode()).hexdigest()


def _cases(inputs: dict) -> dict:
    cases = inputs.get('cases')
    if inputs.get('schema_version') != 1 or not isinstance(inputs.get('dataset_id'), str):
        raise ValueError('inputs require schema_version=1 and dataset_id')
    if not isinstance(cases, list) or not cases:
        raise ValueError('inputs.cases must be a nonempty list')
    by_id = {}
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError('each case must be an object')
        cid = case.get('case_id')
        if not isinstance(cid, str) or not cid or cid in by_id:
            raise ValueError(f'invalid or duplicate case_id: {cid!r}')
        if case.get('task_type') not in TASK_LABELS:
            raise ValueError(f'{cid}: unknown task_type')
        by_id[cid] = case
    return by_id


def _labels(document: dict, field: str, dataset_id: str, cases: dict) -> dict:
    if document.get('schema_version') != 1 or document.get('dataset_id') != dataset_id:
        raise ValueError(f'{field}: schema_version/dataset_id mismatch')
    rows = document.get(field)
    if not isinstance(rows, dict):
        raise ValueError(f'{field} must be an object keyed by case_id')
    missing, extra = set(cases) - set(rows), set(rows) - set(cases)
    if missing or extra:
        raise ValueError(f'{field} membership mismatch: missing={sorted(missing)}, extra={sorted(extra)}')
    labels = {}
    for cid, row in rows.items():
        if not isinstance(row, dict) or row.get('label') not in TASK_LABELS[cases[cid]['task_type']]:
            raise ValueError(f'{cid}: invalid {field} label for {cases[cid]["task_type"]}')
        labels[cid] = row['label']
    return labels


def export_inputs(dataset: Path, output: Path) -> None:
    """Read only inputs.json: evaluator answers need not exist or be accessible."""
    inputs = read_json_strict(Path(dataset) / 'inputs.json')
    _cases(inputs)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inputs, indent=2, ensure_ascii=False) + '\n', encoding='utf8')


def check_corpus(dataset: Path) -> dict:
    """Validate deterministic fixture integrity without scoring any model."""
    from skillvariants.comparison import compare_documents
    from skillvariants.parser import parse_skill_md
    from skillvariants.study.evidence import validate_paired_evidence
    inputs = read_json_strict(Path(dataset) / 'inputs.json')
    expected = read_json_strict(Path(dataset) / 'expected.json')
    cases = _cases(inputs)
    labels = _labels(expected, 'expected', inputs['dataset_id'], cases)
    source_count = citation_count = coverage_count = 0
    for cid, case in cases.items():
        if case['task_type'] in ('change_direction', 'citation_integrity'):
            for side in ('a', 'b'):
                source = case.get(side)
                if not isinstance(source, dict) or not isinstance(source.get('text'), str):
                    raise ValueError(f'{cid}.{side}: source text required')
                digest = hashlib.sha256(source['text'].encode('utf8')).hexdigest()
                if source.get('raw_sha256') != digest:
                    raise ValueError(f'{cid}.{side}: source hash mismatch')
                if source.get('coverage') not in ('full_document', 'excerpt'):
                    raise ValueError(f'{cid}.{side}: explicit source coverage required')
                source_count += 1
        if case['task_type'] == 'citation_integrity':
            comparison = compare_documents(parse_skill_md(case['a']['text']), parse_skill_md(case['b']['text']))
            try:
                validate_paired_evidence({'group_id': 1, 'comparison': comparison},
                                         case.get('citation'), case.get('change_type'))
                outcome = 'VALID'
            except ValueError:
                outcome = 'INVALID'
            if outcome != labels[cid]:
                raise ValueError(f'{cid}: authored citation expectation disagrees with production validator')
            citation_count += 1
        elif case['task_type'] == 'task_coverage':
            dispatched, returned = case.get('dispatched_group_ids'), case.get('returned_group_ids')
            if (not isinstance(dispatched, list) or not isinstance(returned, list)
                    or any(type(gid) is not int for gid in dispatched + returned)
                    or len(dispatched) != len(set(dispatched))):
                raise ValueError(f'{cid}: malformed coverage case')
            outcome = ('COMPLETE' if set(dispatched) == set(returned)
                       and len(returned) == len(set(returned)) else 'INCOMPLETE')
            if outcome != labels[cid]:
                raise ValueError(f'{cid}: authored coverage expectation disagrees with exact membership')
            coverage_count += 1
    return {'dataset_id': inputs['dataset_id'], 'case_count': len(cases),
            'source_hashes_checked': source_count, 'citation_cases_checked': citation_count,
            'coverage_cases_checked': coverage_count, 'model_predictions_evaluated': 0,
            'inputs_sha256': canonical_hash(inputs), 'expected_sha256': canonical_hash(expected),
            'limitations': 'Integrity checks validate corpus structure and exact contract traps; semantic gold labels remain author judgments. No model accuracy was measured.'}


def score_predictions(inputs: dict, expected: dict, predictions: dict) -> dict:
    cases = _cases(inputs)
    gold = _labels(expected, 'expected', inputs['dataset_id'], cases)
    answers = _labels(predictions, 'predictions', inputs['dataset_id'], cases)
    run = predictions.get('run', {})
    if not isinstance(run, dict):
        raise ValueError('run provenance must be an object')
    confusion, details = {}, []
    answered = correct = answered_correct = abstention_required = abstention_correct = 0
    for cid, case in cases.items():
        kind, label, answer = case['task_type'], gold[cid], answers[cid]
        if kind not in confusion:
            confusion[kind] = {actual: {pred: 0 for pred in TASK_LABELS[kind]}
                               for actual in TASK_LABELS[kind]}
        confusion[kind][label][answer] += 1
        is_answered, is_correct = answer != 'ABSTAIN', answer == label
        answered += is_answered
        correct += is_correct
        answered_correct += is_correct and is_answered
        abstention_required += label == 'ABSTAIN'
        abstention_correct += label == answer == 'ABSTAIN'
        details.append({'case_id': cid, 'task_type': kind, 'expected': label,
                        'predicted': answer, 'correct': is_correct, 'abstained': not is_answered})
    count = len(cases)
    return {
        'schema_version': 1, 'dataset_id': inputs['dataset_id'],
        'evaluation_kind': 'author_labeled_synthetic_cases', 'run': run,
        'inputs_sha256': canonical_hash(inputs), 'expected_sha256': canonical_hash(expected),
        'predictions_sha256': canonical_hash(predictions),
        'summary': {
            'total_cases': count, 'returned_cases': count, 'membership_complete': True,
            'answered_cases': answered, 'abstained_cases': count - answered,
            'correct_decisions': correct, 'incorrect_decisions': count - correct,
            'coverage': answered / count,
            'accuracy_on_answered': answered_correct / answered if answered else None,
            'decision_accuracy': correct / count,
            'required_abstention_cases': abstention_required,
            'required_abstention_accuracy': abstention_correct / abstention_required if abstention_required else None,
            'unsupported_answers_on_incomplete_sources': sum(gold[cid] == 'ABSTAIN' and answers[cid] != 'ABSTAIN' for cid in cases),
        },
        'metric_definitions': {
            'coverage': 'Non-ABSTAIN predictions / all cases; missing responses are rejected, not treated as abstentions.',
            'accuracy_on_answered': 'Correct non-ABSTAIN predictions / non-ABSTAIN predictions; null if none answered.',
            'decision_accuracy': 'All labels matching authored gold / all cases, including correct required abstentions.',
            'confusion_by_task': 'Rows are expected labels; columns are predicted labels, including ABSTAIN.',
        },
        'confusion_by_task': confusion, 'cases': details,
        'errors': [detail for detail in details if not detail['correct']],
        'limitations': LIMITATIONS,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=ROOT / 'evals' / 'direction-v1')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('check', help='Check hashes, case ids and deterministic traps; no model scoring.')
    export = commands.add_parser('export', help='Export inputs without reading expected.json.')
    export.add_argument('--out', type=Path, required=True)
    score = commands.add_parser('score', help='Score externally supplied predictions against evaluator answers.')
    score.add_argument('predictions', type=Path)
    score.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'export':
            export_inputs(args.dataset, args.out)
            result = {'exported_inputs': str(args.out), 'evaluator_answers_included': False}
        elif args.command == 'check':
            result = check_corpus(args.dataset)
        else:
            predictions = read_json_strict(args.predictions)
            check_corpus(args.dataset)
            result = score_predictions(read_json_strict(args.dataset / 'inputs.json'),
                                       read_json_strict(args.dataset / 'expected.json'), predictions)
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
        print(json.dumps(result, indent=2, ensure_ascii=True))
    except (ValueError, OSError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
