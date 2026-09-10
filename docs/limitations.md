# Limitations

## Discovery and ranking

Search is a bounded GitHub Code Search query for a frontmatter name, not an exhaustive census. Renamed skills, private repositories, unindexed content and failures can be absent. Search order and coverage change over time. Counts disclose candidates, successful fetches, unique normalized contents, gated results and occurrences separately.

Similarity combines text and structural heuristics. It cannot reliably detect opposite meanings, behavioral equivalence or relevance in every domain. Archetypes help browsing; they are neither a quality score nor a recommendation. The reversal regression prevents one known text change from being hidden, not all possible semantic mistakes.

Normalization can collapse raw formatting differences. Occurrences retain separate raw hashes. Shared content or repositories do not prove independent adoption, influence or ancestry.

## Source evidence

Line-numbered hunks contain limited context. Truncation is explicit; omitted context must be read from hash-checked snapshots or left unresolved. Even a complete quote cannot establish that an interpretation is correct. Full-source review is an agent assertion backed by checked excerpts; the engine cannot prove that the agent considered every line.

A study stores available raw snapshots independently of the general cache. Offline operation requires previously cached inputs. Local full-file inspection and comparison do not use the network.

## Experimental semantics

The engine does not call an LLM. Your agent supplies proposals, consolidation and verification. A separate task may use the same model and context; independence is not guaranteed by the runtime. NO and UNCERTAIN verifier decisions are excluded from recurring counts.

All proposed members must be verified in chunks of at most eight. Fewer than three supporting groups cannot recur. Clusters above fifteen are suppressed as SPLIT_REQUIRED; automated iterative splitting is not implemented. A rejection share above 20% is suppressed rather than broadened into acceptance.

Reports distinguish initial observations, reviewed interpretations, deterministic counts and unresolved sources. Optional analyst prose is stored separately. COMPLETE means the workflow ended and artifacts exist; it does not imply complete corpus coverage, correct semantics or useful advice.

## Validation and use

Historical benchmark scripts replayed existing annotations and partially copied stability runs. Their metrics are not independent model-quality evidence. New synthetic cases test a defined protocol and include a separately submitted annotation exercise, but do not establish performance on representative GitHub data.

No representative maintainer study or measured time saving has been completed. Do not infer security, best practices or real agent execution from text comparisons. Read unfamiliar source content as untrusted data.
