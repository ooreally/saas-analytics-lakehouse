# Databricks notebook source
# MAGIC %md
# MAGIC # 00 Setup Workspace
# MAGIC
# MAGIC Creates the bronze, silver, gold, ops, and quarantine schemas plus the shared ops tables.

# COMMAND ----------
from pathlib import Path
import sys

repo_root = Path.cwd().resolve()
for candidate in [repo_root, *repo_root.parents]:
    if (candidate / "conf" / "project_config.yml").exists():
        repo_root = candidate
        break

src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.append(str(src_root))

from creative_analytics_platform.audit import build_audit_record, utc_now_iso
from creative_analytics_platform.config import ProjectConfig
from creative_analytics_platform.runtime import append_audit_record

try:
    dbutils.widgets.text("batch_id", "2026-03-01")
    batch_id = dbutils.widgets.get("batch_id")
except NameError:
    batch_id = "2026-03-01"

config = ProjectConfig.from_path(repo_root / "conf" / "project_config.yml")
started_at = utc_now_iso()

for layer in ("bronze", "silver", "gold", "ops", "quarantine"):
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {config.catalog}.{config.schema_name(layer)}")

spark.sql(
    f"""
    CREATE TABLE IF NOT EXISTS {config.audit_table_name()} (
      step_name STRING,
      batch_id STRING,
      status STRING,
      input_count BIGINT,
      output_count BIGINT,
      message STRING,
      started_at STRING,
      ended_at STRING,
      duration_seconds INT
    ) USING DELTA
    """
)

spark.sql(
    f"""
    CREATE TABLE IF NOT EXISTS {config.quality_table_name()} (
      check_name STRING,
      target_name STRING,
      status STRING,
      observed_value STRING,
      details STRING,
      batch_id STRING,
      checked_at STRING
    ) USING DELTA
    """
)

spark.sql(
    f"""
    CREATE TABLE IF NOT EXISTS {config.summary_table_name()} (
      batch_id STRING,
      asset_name STRING,
      row_count BIGINT,
      notes STRING,
      generated_at STRING
    ) USING DELTA
    """
)

ended_at = utc_now_iso()
append_audit_record(
    spark,
    config.audit_table_name(),
    build_audit_record(
        step_name="setup_workspace",
        batch_id=batch_id,
        status="SUCCESS",
        input_count=0,
        output_count=5,
        message="Created schemas and shared ops tables",
        started_at=started_at,
        ended_at=ended_at,
    ),
)

display(spark.sql(f"SHOW TABLES IN {config.catalog}.{config.schema_name('ops')}"))
