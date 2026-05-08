# Databricks notebook source
# MAGIC %md
# MAGIC # 10 Bronze Ingestion
# MAGIC
# MAGIC Reads the checked-in raw CSV drops, adds ingestion metadata, and merges them into bronze Delta tables.

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
from creative_analytics_platform.runtime import append_audit_record, merge_into_delta, read_drop_records
from creative_analytics_platform.transforms import add_ingestion_metadata

try:
    dbutils.widgets.text("batch_id", "2026-03-01")
    batch_id = dbutils.widgets.get("batch_id")
except NameError:
    batch_id = "2026-03-01"

config = ProjectConfig.from_path(repo_root / "conf" / "project_config.yml")
contracts = load_all_contracts(repo_root / "conf" / "schemas")

for entity, contract in contracts.items():
    started_at = utc_now_iso()
    raw_rows = read_drop_records(repo_root, batch_id, entity)
    if not raw_rows:
        append_audit_record(
            spark,
            config.audit_table_name(),
            build_audit_record(
                step_name=f"bronze_{entity}",
                batch_id=batch_id,
                status="SKIPPED",
                input_count=0,
                output_count=0,
                message=f"No file found for {entity} in batch {batch_id}",
                started_at=started_at,
                ended_at=utc_now_iso(),
            ),
        )
        continue

    loaded_at = utc_now_iso()
    enriched_rows = add_ingestion_metadata(raw_rows, batch_id=batch_id, source_file=f"{entity}.csv", loaded_at=loaded_at)
    dataframe = spark.createDataFrame(enriched_rows)
    target_table = config.full_table_name("bronze", entity)
    merge_into_delta(spark, target_table, dataframe, contract.primary_key + ["_batch_id"])

    append_audit_record(
        spark,
        config.audit_table_name(),
        build_audit_record(
            step_name=f"bronze_{entity}",
            batch_id=batch_id,
            status="SUCCESS",
            input_count=len(raw_rows),
            output_count=dataframe.count(),
            message=f"Merged bronze rows for {entity}",
            started_at=started_at,
            ended_at=utc_now_iso(),
        ),
    )

display(spark.sql(f"SHOW TABLES IN {config.catalog}.{config.schema_name('bronze')}"))
