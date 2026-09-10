# Evaluation: synthetic contract checks and external predictions

The evaluation tools separate authored cases, evaluator answers and externally supplied predictions. They do not call a model or turn an oracle replay into an accuracy claim.

## Datasets and provenance

| Dataset | Scope | What its checks establish |
|---|---|---|
| `evals/direction-v1/` | 16 original, short, focused document pairs: additions, removals, polarity/condition changes, preservation, paraphrase, relocation and incomplete-source abstention | Raw source integrity and a versioned set of author-defined semantic expectations |
| `evals/contract-v1/` | 8 original quote/hash and exact-membership traps | Deterministic citation validation and complete, unique task membership |

Each directory contains `inputs.json` and a separate `expected.json`. The inputs contain source text, SHA-256 hashes, explicit source scope and task instructions. The expected file contains evaluator labels and rationales. Neither dataset contains captured third-party Skill text. Dataset construction and initial answer authorship used GPT-6 Astra at high reasoning; these are author judgments, not independently adjudicated human gold labels.

`check` verifies source hashes, unique case ids, exact expected-answer membership and valid label sets. Citation cases also run through the production paired-evidence validator. Membership cases check that every requested id occurs exactly once with no extras. Semantic gold labels are not machine-proven by these checks.

## Run deterministic checks

From the repository root, with SkillVariants installed in the active Python environment:

```sh
python scripts/evaluate_contract.py check
python scripts/evaluate_contract.py --dataset evals/contract-v1 check
python -m pytest tests/test_evaluation_contract.py -q
```

The check output explicitly reports `model_predictions_evaluated: 0`. These commands validate the evaluation assets and scorer; they do not measure model quality.

## Collect independent predictions

Export only the inputs:

```sh
python scripts/evaluate_contract.py export --out /path/to/isolated-run/inputs.json
```

The exporter reads only `inputs.json`; it works even when `expected.json` is absent. Give the annotator that exported file and the prediction format below. Do not provide `expected.json`, previous results, evaluator rationales, or answer-derived examples. Restrict repository access where practical and record the actual context boundary. A file named “blind” does not by itself establish independence.

Use a new run directory and provide exactly one object per input case id:

```json
{
  "schema_version": 1,
  "dataset_id": "direction-v1",
  "run": {
    "producer": "actual annotator identifier",
    "mode": "blind-declared",
    "model": "actual model or human",
    "notes": "State which files and prior context were available."
  },
  "predictions": {
    "d001": {"label": "ABSTAIN", "reason": "Replace with this case's independent decision."}
  }
}
```

The abbreviated example is a format illustration, not a valid complete submission. Direction labels are `ADDED`, `REMOVED`, `MODIFIED`, `UNCHANGED` and `ABSTAIN`. The contract dataset uses `VALID`/`INVALID` for citations and `COMPLETE`/`INCOMPLETE` for membership, with `ABSTAIN` permitted. Reasons are retained in the prediction artifact but are not automatically graded for semantic support.

The loader rejects duplicate JSON keys. Missing ids, extra ids, invalid labels and wrong dataset ids reject the entire score request. Missing responses are never silently converted into abstentions. Record an explicit `ABSTAIN` when the supplied source scope is insufficient.

Freeze inputs, expected answers and predictions before scoring:

```sh
python scripts/evaluate_contract.py score evals/runs/my-run/predictions.json --out evals/runs/my-run/results.json
```

For the contract dataset, add `--dataset evals/contract-v1` before `score`. A result records canonical JSON hashes for inputs, expected answers and predictions, a complete confusion matrix, every case decision and an explicit error list. Amendments after scoring require a new dataset/run version and a stated correction; do not tune the gold to improve a recorded result.

## Metric denominators

- **Membership completion:** all required prediction ids were present exactly once; otherwise no score is produced.
- **Coverage:** non-ABSTAIN predictions divided by all cases.
- **Accuracy on answered cases:** matching non-ABSTAIN predictions divided by non-ABSTAIN predictions. It is `null` when every case is abstained.
- **Decision accuracy:** all predictions matching authored labels divided by all cases, including correctly required abstentions.
- **Required-abstention accuracy:** matching ABSTAIN decisions divided by cases whose authored answer is ABSTAIN.
- **Confusion:** expected labels are rows and predicted labels are columns; ABSTAIN is included.

Coverage is not confidence, and accurately quoting text does not prove that the proposed behavioral interpretation follows from it. No metric here measures independence of adoption, maintainer usefulness, multilingual generalization, repository-scale retrieval recall, long-document reasoning or resistance to source prompt injection.

## Recorded separate annotation exercise

The [2026-09-10 run](../evals/runs/astra-high-blind-2026-09-10/README.md) used a separate GPT-6 Astra high agent that declared access only to the input file for annotation. Its pre-existing implementation context and shared model family remain material limitations. It returned all 16 decisions: 14 substantive answers and 2 abstentions. The one recorded scoring pass found all 16 decisions matched the author-defined labels, with 87.5% answer coverage and no mismatches on this small dataset.

This is a same-model synthetic exercise, not a general accuracy estimate or external validation. Preserve its full prediction/result artifacts and the absence of observed errors; do not extrapolate the result into a product-quality claim.

## Historical research results

Earlier spike benchmarks and studies under `research/` may replay known agent labels, use examples seen while developing the heuristics, or report structural grouping counts. Treat those as historical replay/development evidence unless their independent input boundary, frozen predictions and evaluator answers can be demonstrated. A perfect replay establishes that a pipeline can reproduce supplied answers; it does not measure a model's ability to discover unknown behavioral changes.

The current foundation makes future independent runs possible. It still needs larger independently authored cases, human adjudication, difficult near-misses, long and multilingual source documents, explicit cost/latency measurement, and evaluation of whether maintainers find useful differences faster.
