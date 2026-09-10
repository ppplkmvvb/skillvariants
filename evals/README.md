# Evaluation assets

See [the evaluation guide](../docs/evaluation.md) for provenance, commands, prediction schema and metric definitions.

- `direction-v1/inputs.json`: 16 original semantic-direction inputs, suitable for export to a separate annotator.
- `direction-v1/expected.json`: author-defined evaluator labels and rationales; exclude from annotator context.
- `contract-v1/`: eight original citation/hash and complete-membership traps with separate expected answers.
- `runs/`: immutable external prediction artifacts and separately generated scoring results.

These files are original project-authored synthetic evaluation material, covered by the repository license. They are not upstream Skill captures. Do not expose evaluator answers or previous results to an annotator whose run will be described as blind. Do not report oracle/self-test replay as independent model accuracy.
