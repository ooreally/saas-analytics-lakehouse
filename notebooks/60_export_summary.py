# Databricks notebook source
# MAGIC %md
# MAGIC # 60 Export Summary
# MAGIC
# MAGIC Captures row counts for the main gold assets and stores a compact run summary in the ops schema.

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
from creative_analytics_platform.runtime import append_audit_record, append_rows

try:
    dbutils.widgets.text("batch_id", "2026-03-01")
    batch_id = dbutils.widgets.get("batch_id")
except NameError:
    batch_id = "2026-03-01"

config = ProjectConfig.from_path(repo_root / "conf" / "project_config.yml")

summary_rows = []
for table_name in config.gold_tables:
    full_name = config.full_table_name("gold", table_name)
    row_count = spark.table(full_name).count()
    summary_rows.append(
        {
            "batch_id": batch_id,
            "asset_name": table_name,
            "row_count": row_count,
            "notes": "Gold analytics output ready for screenshots or BI handoff",
            "generated_at": utc_now_iso(),
        }
    )

started_at = utc_now_iso()
append_rows(spark, config.summary_table_name(), summary_rows)
append_audit_record(
    spark,
    config.audit_table_name(),
    build_audit_record(
        step_name="export_summary",
        batch_id=batch_id,
        status="SUCCESS",
        input_count=len(summary_rows),
        output_count=len(summary_rows),
        message="Wrote summary rows for gold outputs",
        started_at=started_at,
        ended_at=utc_now_iso(),
    ),
)

display(spark.table(config.summary_table_name()).filter(f"batch_id = '{batch_id}'"))
