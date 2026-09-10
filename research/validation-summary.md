# Validation status and historical correction

Updated 2026-09-10. This replaces the former summary of historical success metrics.

The deterministic core has offline fixtures and targeted regressions for discovery, ranking, paired evidence, runtime integrity and installed commands. Five known adaptation anchors were found in a replay of the original cached corpus during review. This is a known-anchor cached result, not measured recall over GitHub or a fresh acquisition.

The earlier semantic benchmark driver consumed existing annotated rows: the 243 replayed labels/actions matched those rows. A later stability run copied the first output with a few edits. Thus the prior “0% over-merge,” “100% stability” and “human-audited groups” descriptions do not establish independent model quality.

A recurring stop/escalation rule was also described as ADDED even though the target already contained it. This demonstrated a missing direction-of-change check. Schema 2 now requires paired exact citations and an explicit direction; independent semantic accuracy still needs evaluation.

An earlier audit inferred nineteen default-YES verifier results. On reinspection those nineteen entries were in clusters below the recurring threshold and skipped by that historical script; zero such default-YES fallbacks were reached in the frozen recurring clusters. The fallback was a code hazard, not evidence that those nineteen groups were accepted.

The current [evaluation protocol](../docs/evaluation.md) separates inputs, expected answers and predictions, publishes abstentions and errors, and states the limitations of the small same-model synthetic exercise. New source/runtime/CLI regressions and installed-wheel checks are engineering evidence. None of these establishes user value, model performance across arbitrary skills, independent adoption or best practices.
