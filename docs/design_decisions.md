# Design Decisions

## Why notebooks plus modules
The goal is to show Databricks-native delivery while still signaling software engineering discipline. Notebooks make the orchestration story readable for recruiters, while `src/` keeps the logic reusable and testable.

## Why batch instead of streaming
Databricks Free Edition is serverless-only and quota-limited. Batch incremental drops still show the important engineering behaviors for the target role: `MERGE`, late-arrival handling, dedupe, quality checks, and curated analytics tables.

## Why a mock LLM default
The Adobe role expects recent GenAI or LLM exposure, but the repo should remain runnable without paid APIs or workspace-specific model serving. The mock provider gives deterministic topic classification and summarization while the external provider keeps the interface extensible.

## Why JSON-compatible YAML
Using JSON-compatible YAML for config and contracts avoids an unnecessary parser dependency in local tests, while preserving the `.yml` interface expected in modern data repos.
