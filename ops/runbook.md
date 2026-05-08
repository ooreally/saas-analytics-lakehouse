# Runbook

## Goal
Run the full analytics pipeline end to end and verify that bronze, silver, gold, audit, quarantine, and quality outputs are created correctly.

## Preconditions
- Repo is imported into a Databricks workspace or Databricks Repo.
- A Spark session is available.
- `conf/project_config.yml` still points to the intended catalog and schema prefix.
- If testing a real LLM provider, the environment variable named in `external_llm_api_key_env` is configured.

## Standard Run
1. Run `notebooks/00_setup_workspace.py`.
2. Run the Lakeflow Job from `ops/job_definition.yml` with `batch_id=2026-03-01`.
3. Rerun the same job with `batch_id=2026-03-05`.
4. Rerun the same job with `batch_id=2026-03-07_late_arrivals`.
5. Review:
   - `main.creative_saas_analytics_ops.pipeline_audit`
   - `main.creative_saas_analytics_ops.data_quality_results`
   - `main.creative_saas_analytics_quarantine.*`
   - all six gold tables

## Expected Highlights
- `E099` is quarantined because `download_export` is outside the allowed event enum.
- `E024` only appears once in silver after dedupe.
- `T002` is updated to `resolved` after the late-arrival batch.
- `S002` upgrades from `trial` to `professional`.

## Failure Triage
- If a notebook cannot import `src/`, rerun from a Databricks Repo or update `repo_root` detection.
- If `MERGE` fails, confirm the target table exists in Delta format.
- If external LLM mode fails, switch config back to `mock` and rerun `40_llm_enrichment.py`.
