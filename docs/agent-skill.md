# Use SkillVariants from an agent

Install the CLI from the same revision as the Agent Skill. Copy the complete `skills/skillvariants/` directory, including its references and example, into your agent's supported skills directory. The Python wheel installs the command; the separate Skill ZIP installs instructions.

Start with a specific comparison request. A full study is useful only when you need to analyze a bounded corpus for recurring adaptations.

Example prompt:

> Find relevant adaptations of this Skill. Show a small shortlist and compare the instruction changes against the target. Cite both sources. If evidence is incomplete, say what is missing.

For a full study:

> Study the recurring behavioral changes to this Skill. Use SkillVariants task dispatch and source snapshots, preserve unresolved evidence, and separate observations from interpretations.

The agent uses the CLI already on PATH. Do not silently run an old PyPI version for a newer task schema.

```bash
skillvariants study-start <SKILL.md-url> --json
skillvariants study-next <study-id> --json
skillvariants study-submit <study-id> <task-result.json> --json
skillvariants study-status <study-id> --json
skillvariants study-report <study-id> --json
```

Repeat next → perform task → submit until COMPLETE. `--base-dir` is a workspace root, appended once with `.skillvariants/studies`; use the same root for all study commands.

The runtime validates ids, exact task membership, source hashes, quoted lines and enums. The agent must still decide whether a passage supports the interpretation. A full-source citation requires reading the dispatched, hash-checked snapshot. Incomplete material must remain unresolved if it cannot be recovered.

Pass B clusters by behavioral equivalence and change direction. Every proposed recurring member receives a separate verifier decision; YES needs its own paired citations. You may assign verification to another model or reviewer, but the runtime does not enforce reviewer independence.

The engine generates report.json and report.md. The final task can accept optional analyst notes saved separately; it cannot replace generated counts or evidence. See the [runtime contract](agent-runtime.md) and [bundled Skill](../skills/skillvariants/SKILL.md).
