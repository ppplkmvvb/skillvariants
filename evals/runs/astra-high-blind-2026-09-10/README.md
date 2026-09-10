# Separate synthetic annotation run — 2026-09-10

This run used `evals/direction-v1/inputs.json` and a separate GPT-6 Astra agent with high reasoning. The annotator declared that only the input file was read for annotation, while prior implementation context remained available. The case author and annotator used the same model family. This is a procedurally separate, same-model synthetic exercise, not independent external validation or a general accuracy estimate.

The evaluator answers were authored before annotation and kept in a separate file. The root coordinator and annotator reported not reading them before predictions were saved. The author/evaluator then ran the scorer once. Inputs, expected answers and predictions were not revised after viewing that result.

Artifacts:

- `predictions.json`: externally supplied case-keyed decisions and actual annotator provenance.
- `results.json`: the single scoring output, including canonical hashes, all decisions, confusion matrix and the error list.

Observed result: all 16 case ids were returned; 14 received substantive labels and two were abstained. All 16 decisions matched the author-defined expectations. Answer coverage was 87.5%; accuracy on answered cases was 14/14. The result artifact records zero mismatches and zero unsupported answers on the incomplete-source cases.

The absence of errors on these short authored cases is not evidence of general reliability. No real-world prevalence, maintainer benefit, retrieval recall, multilingual performance, long-document performance or model cost was measured. The scorer grades labels against authored answers; it does not verify the semantic correctness of free-text reasons.

Reproduction from the repository root (writes a new output, preserving the recorded result):

```sh
python scripts/evaluate_contract.py score evals/runs/astra-high-blind-2026-09-10/predictions.json --out /path/to/reproduced-results.json
```
