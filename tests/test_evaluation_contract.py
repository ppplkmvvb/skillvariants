"""Score external decisions honestly, preserving abstention and exact membership."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'evaluate_contract.py'


def harness():
    assert SCRIPT.is_file(), 'evaluation CLI is not implemented'
    spec = importlib.util.spec_from_file_location('evaluation_contract', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def minimal_scores():
    inputs = {'schema_version': 1, 'dataset_id': 'small-test', 'cases': [
        {'case_id': case_id, 'task_type': 'change_direction'} for case_id in ('one', 'two', 'three')]}
    expected = {'schema_version': 1, 'dataset_id': 'small-test', 'expected': {
        'one': {'label': 'ADDED'}, 'two': {'label': 'REMOVED'}, 'three': {'label': 'ABSTAIN'}}}
    predictions = {'schema_version': 1, 'dataset_id': 'small-test',
                   'run': {'producer': 'unit test', 'mode': 'self-test'}, 'predictions': {
                       'one': {'label': 'MODIFIED'}, 'two': {'label': 'REMOVED'},
                       'three': {'label': 'ABSTAIN'}}}
    return inputs, expected, predictions


def test_score_separates_coverage_answer_accuracy_and_required_abstention():
    result = harness().score_predictions(*minimal_scores())
    assert result['summary']['total_cases'] == 3
    assert result['summary']['answered_cases'] == 2
    assert result['summary']['abstained_cases'] == 1
    assert result['summary']['correct_decisions'] == 2
    assert result['summary']['coverage'] == pytest.approx(2 / 3)
    assert result['summary']['accuracy_on_answered'] == 0.5
    assert result['summary']['decision_accuracy'] == pytest.approx(2 / 3)
    assert result['summary']['required_abstention_accuracy'] == 1
    confusion = result['confusion_by_task']['change_direction']
    assert confusion['ADDED']['MODIFIED'] == 1
    assert confusion['ABSTAIN']['ABSTAIN'] == 1
    assert result['run']['mode'] == 'self-test'
    assert 'not independent' in result['limitations'].lower()


@pytest.mark.parametrize('defect', ['missing', 'extra', 'wrong_label', 'wrong_dataset'])
def test_invalid_prediction_membership_or_schema_is_rejected(defect):
    inputs, expected, predictions = minimal_scores()
    if defect == 'missing':
        predictions['predictions'].pop('two')
    elif defect == 'extra':
        predictions['predictions']['surprise'] = {'label': 'ADDED'}
    elif defect == 'wrong_label':
        predictions['predictions']['two']['label'] = 'VALID'
    else:
        predictions['dataset_id'] = 'different-corpus'
    with pytest.raises(ValueError):
        harness().score_predictions(inputs, expected, predictions)


def test_duplicate_json_prediction_keys_are_not_silently_overwritten(tmp_path):
    path = tmp_path / 'duplicate.json'
    path.write_text('{"predictions":{"one":{"label":"ADDED"},"one":{"label":"REMOVED"}}}', encoding='utf8')
    with pytest.raises(ValueError, match='duplicate'):
        harness().read_json_strict(path)


def test_all_abstentions_report_null_answered_accuracy():
    inputs, expected, predictions = minimal_scores()
    for value in predictions['predictions'].values():
        value['label'] = 'ABSTAIN'
    result = harness().score_predictions(inputs, expected, predictions)
    assert result['summary']['coverage'] == 0
    assert result['summary']['accuracy_on_answered'] is None
    assert result['summary']['correct_decisions'] == 1


def test_export_does_not_read_or_include_evaluator_answers(tmp_path):
    module = harness()
    dataset = tmp_path / 'input-only'
    dataset.mkdir()
    inputs = json.loads((ROOT / 'evals/direction-v1/inputs.json').read_text(encoding='utf8'))
    (dataset / 'inputs.json').write_text(json.dumps(inputs), encoding='utf8')
    out = tmp_path / 'blind-inputs.json'
    module.export_inputs(dataset, out)
    exported = module.read_json_strict(out)
    assert exported == inputs
    assert 'expected' not in exported
    assert 'rationale' not in json.dumps(exported)


def test_corpus_integrity_checks_cover_direction_and_contract_traps():
    module = harness()
    direction = module.check_corpus(ROOT / 'evals/direction-v1')
    contract = module.check_corpus(ROOT / 'evals/contract-v1')
    assert direction['case_count'] == 16
    assert contract['citation_cases_checked'] >= 3
    assert contract['coverage_cases_checked'] >= 3
    assert direction['model_predictions_evaluated'] == 0
    assert contract['model_predictions_evaluated'] == 0


def test_source_hash_corruption_fails_integrity_check(tmp_path):
    module = harness()
    inputs = module.read_json_strict(ROOT / 'evals/direction-v1/inputs.json')
    expected = module.read_json_strict(ROOT / 'evals/direction-v1/expected.json')
    inputs['cases'][0]['a']['text'] += 'changed without updating its source hash'
    (tmp_path / 'inputs.json').write_text(json.dumps(inputs), encoding='utf8')
    (tmp_path / 'expected.json').write_text(json.dumps(expected), encoding='utf8')
    with pytest.raises(ValueError, match='hash'):
        module.check_corpus(tmp_path)


def test_real_cli_rejects_duplicate_keys_with_actionable_error(tmp_path):
    harness()
    path = tmp_path / 'bad.json'
    path.write_text('{"predictions":{"d001":{},"d001":{}}}', encoding='utf8')
    result = subprocess.run([sys.executable, '-B', str(SCRIPT), 'score', str(path)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 2
    assert 'duplicate' in result.stderr and 'Traceback' not in result.stderr
