# Databricks notebook source
# MAGIC %md
# MAGIC # 20 Silver Transforms
# MAGIC
# MAGIC Applies contract validation, dedupe, masking, and normalization. Invalid rows are merged into quarantine tables.

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
from creative_analytics_platform.contracts import load_all_contracts
from creative_analytics_platform.quality import split_valid_invalid
from creative_analytics_platform.runtime import append_audit_record, merge_into_delta, spark_table_exists
from creative_analytics_platform.transforms import (
    dedupe_records,
    normalize_subscription_record,
    normalize_support_record,
    sanitize_user_record,
)

try:
    dbutils.widgets.text("batch_id", "2026-03-01")
    batch_id = dbutils.widgets.get("batch_id")
except NameError:
    batch_id = "2026-03-01"

config = ProjectConfig.from_path(repo_root / "conf" / "project_config.yml")
contracts = load_all_contracts(repo_root / "conf" / "schemas")

for entity, contract in contracts.items():
    started_at = utc_now_iso()
    bronze_table = config.full_table_name("bronze", entity)
    if not spark_table_exists(spark, bronze_table):
        continue

    bronze_rows = [row.asDict(recursive=True) for row in spark.table(bronze_table).collect()]
    valid_rows, invalid_rows = split_valid_invalid(contract, bronze_rows)
    deduped_rows = dedupe_records(valid_rows, contract.primary_key, "_loaded_at")

    if entity == "users_workspaces":
        silver_rows = [sanitize_user_record(row) for row in deduped_rows]
    elif entity == "subscriptions":
        silver_rows = [normalize_subscription_record(row) for row in deduped_rows]
    elif entity == "support_feedback":
        silver_rows = [normalize_support_record(row) for row in deduped_rows]
    else:
        silver_rows = deduped_rows

    for row in silver_rows:
        row["_silver_updated_at"] = utc_now_iso()

    if silver_rows:
        silver_df = spark.createDataFrame(silver_rows)
        merge_into_delta(spark, config.full_table_name("silver", entity), silver_df, contract.primary_key)

    if invalid_rows:
        invalid_df = spark.createDataFrame(invalid_rows)
        merge_into_delta(
            spark,
            config.quarantine_table_name(entity),
            invalid_df,
            contract.primary_key + ["_batch_id"],
        )

    append_audit_record(
        spark,
        config.audit_table_name(),
        build_audit_record(
            step_name=f"silver_{entity}",
            batch_id=batch_id,
            status="SUCCESS",
            input_count=len(bronze_rows),
            output_count=len(silver_rows),
            message=f"{len(invalid_rows)} invalid rows moved to quarantine for {entity}",
            started_at=started_at,
            ended_at=utc_now_iso(),
        ),
    )

display(spark.sql(f"SHOW TABLES IN {config.catalog}.{config.schema_name('silver')}"))
