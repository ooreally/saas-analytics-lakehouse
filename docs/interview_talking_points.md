# Interview Talking Points

- I designed the project around Databricks Free Edition constraints so it proves judgment, not just tool familiarity.
- Bronze is append-friendly raw lineage storage; silver applies contract validation, dedupe, normalization, and PII minimization; gold focuses on analytics-ready metrics and experimentation.
- I used idempotent `MERGE` patterns so reruns, duplicate files, and late-arriving batches do not corrupt downstream outputs.
- The support feedback workflow shows how to blend structured and unstructured data without making the platform dependent on a paid model provider.
- The quality layer covers primary keys, null checks, enum checks, duplicate detection, and metric reconciliation, which is closer to real production discipline than a notebook-only prototype.
