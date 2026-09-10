# Worked paired example

The historical systematic-debugging showcase at this path was retired: it described a stop condition as added even though the target already contained one. Do not reuse its old counts or claims.

Use this original illustrative pair instead:

Target:
```text
1. Read the requested change.
2. Write an implementation plan.
3. Do not implement before the user approves the plan.
4. Run the relevant checks.
```

Variant:
```text
1. Read the requested change.
2. Write an implementation plan.
3. Implement the plan before asking for user approval.
4. Run the relevant checks.
```

Observation: the third instruction places approval on opposite sides of implementation.

Interpretation: MODIFIED; the approval order is reversed. This is not an addition of a requirement that was previously absent.

A valid real submission copies each raw hash, hunk id and exact line range from the runtime's comparison. Do not invent hashes from this prose example. A separate verifier should read the pair and can disagree or abstain.

If both versions said to wait for approval using different words, label the focused instruction UNCHANGED. If the target source were truncated before the relevant section, inspect its complete snapshot or escalate rather than claiming that approval was absent.

This example demonstrates an interpretation method; it is not a sampled adaptation or an adoption statistic.
