# Databricks notebook source
# MAGIC %md
# MAGIC # 40 LLM Enrichment
# MAGIC
# MAGIC Enriches support feedback with a mock or external LLM provider and publishes support topic trends.

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
from creative_analytics_platform.llm import build_provider
from creative_analytics_platform.metrics import build_support_topic_trends
from creative_analytics_platform.runtime import append_audit_record, merge_into_delta

try:
    dbutils.widgets.text("batch_id", "2026-03-01")
    batch_id = dbutils.widgets.get("batch_id")
except NameError:
    batch_id = "2026-03-01"

config = ProjectConfig.from_path(repo_root / "conf" / "project_config.yml")
flags = config.feature_flags

provider = build_provider(
    provider_name=flags["llm_provider"],
    api_base=flags["external_llm_base_url"],
    api_key_env=flags["external_llm_api_key_env"],
)

silver_feedback_table = config.full_table_name("silver", "support_feedback")
feedback_rows = [row.asDict(recursive=True) for row in spark.table(silver_feedback_table).collect()]

enriched_rows = []
for row in feedback_rows:
    llm_result = provider.classify_and_summarize(
        row.get("feedback_text", ""),
        {
            "priority": row.get("priority"),
            "product_area": row.get("product_area"),
            "resolution_status": row.get("resolution_status"),
        },
    )
    enriched_row = dict(row)
    enriched_row.update(llm_result)
    enriched_row["_enriched_at"] = utc_now_iso()
    enriched_rows.append(enriched_row)

started_at = utc_now_iso()
enriched_df = spark.createDataFrame(enriched_rows)
merge_into_delta(
    spark,
    config.full_table_name("silver", "support_feedback_enriched"),
    enriched_df,
    ["ticket_id"],
)

topic_trend_rows = build_support_topic_trends(enriched_rows)
topic_trend_df = spark.createDataFrame(topic_trend_rows)
merge_into_delta(
    spark,
    config.full_table_name("gold", "gold_support_topic_trends"),
    topic_trend_df,
    ["feedback_date", "topic"],
)

append_audit_record(
    spark,
    config.audit_table_name(),
    build_audit_record(
        step_name="llm_enrichment",
        batch_id=batch_id,
        status="SUCCESS",
        input_count=len(feedback_rows),
        output_count=len(enriched_rows),
        message=f"Support feedback enriched using provider={flags['llm_provider']}",
        started_at=started_at,
        ended_at=utc_now_iso(),
    ),
)

display(spark.table(config.full_table_name("gold", "gold_support_topic_trends")))
