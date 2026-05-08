# Databricks notebook source
# MAGIC %md
# MAGIC # 50 Quality Validation
# MAGIC
# MAGIC Runs core checks for duplicates, enums, quarantine volume, enriched feedback completeness, and metric reconciliation.

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
from creative_analytics_platform.quality import QualityCheckResult, count_nulls, find_duplicate_keys, reconcile_metric_total
from creative_analytics_platform.runtime import append_audit_record, append_rows

try:
    dbutils.widgets.text("batch_id", "2026-03-01")
    batch_id = dbutils.widgets.get("batch_id")
except NameError:
    batch_id = "2026-03-01"

config = ProjectConfig.from_path(repo_root / "conf" / "project_config.yml")

quality_rows = []

users_rows = [row.asDict(recursive=True) for row in spark.table(config.full_table_name("silver", "users_workspaces")).collect()]
duplicate_users = find_duplicate_keys(users_rows, ["user_id"])
quality_rows.append(
    {
        **QualityCheckResult(
            check_name="primary_key_uniqueness",
            target_name="silver_users_workspaces",
            status="PASS" if not duplicate_users else "FAIL",
            observed_value=str(len(duplicate_users)),
            details="Duplicate user_id count",
        ).as_dict(),
        "batch_id": batch_id,
        "checked_at": utc_now_iso(),
    }
)

subscription_rows = [row.asDict(recursive=True) for row in spark.table(config.full_table_name("silver", "subscriptions")).collect()]
invalid_plan_tiers = [row for row in subscription_rows if row.get("plan_tier") not in {"starter", "professional", "enterprise", "trial"}]
quality_rows.append(
    {
        **QualityCheckResult(
            check_name="plan_tier_enum",
            target_name="silver_subscriptions",
            status="PASS" if not invalid_plan_tiers else "FAIL",
            observed_value=str(len(invalid_plan_tiers)),
            details="Invalid plan tier count",
        ).as_dict(),
        "batch_id": batch_id,
        "checked_at": utc_now_iso(),
    }
)

quarantine_table = config.quarantine_table_name("app_events")
quarantine_count = spark.table(quarantine_table).count() if spark.catalog.tableExists(quarantine_table) else 0
quality_rows.append(
    {
        **QualityCheckResult(
            check_name="invalid_event_name",
            target_name="quarantine_app_events",
            status="WARN" if quarantine_count else "PASS",
            observed_value=str(quarantine_count),
            details="Quarantined app event rows",
        ).as_dict(),
        "batch_id": batch_id,
        "checked_at": utc_now_iso(),
    }
)

silver_events = spark.table(config.full_table_name("silver", "app_events"))
gold_daily = spark.table(config.full_table_name("gold", "gold_daily_product_metrics"))
silver_publish_count = silver_events.filter("event_name = 'publish'").count()
gold_publish_count = gold_daily.selectExpr("coalesce(sum(publish_events), 0) as total_publish_events").collect()[0]["total_publish_events"]
quality_rows.append(
    {
        **QualityCheckResult(
            check_name="publish_metric_reconciliation",
            target_name="gold_daily_product_metrics",
            status="PASS" if reconcile_metric_total(silver_publish_count, gold_publish_count) else "FAIL",
            observed_value=f"silver={silver_publish_count},gold={gold_publish_count}",
            details="Publish counts should reconcile between silver events and gold metrics",
        ).as_dict(),
        "batch_id": batch_id,
        "checked_at": utc_now_iso(),
    }
)

enriched_rows = [row.asDict(recursive=True) for row in spark.table(config.full_table_name("silver", "support_feedback_enriched")).collect()]
null_counts = count_nulls(enriched_rows, ["summary", "topic", "sentiment"])
quality_rows.append(
    {
        **QualityCheckResult(
            check_name="null_summary_fields",
            target_name="silver_support_feedback_enriched",
            status="PASS" if sum(null_counts.values()) == 0 else "FAIL",
            observed_value=str(null_counts),
            details="Summary, topic, and sentiment should all be populated",
        ).as_dict(),
        "batch_id": batch_id,
        "checked_at": utc_now_iso(),
    }
)

started_at = utc_now_iso()
append_rows(spark, config.quality_table_name(), quality_rows)
append_audit_record(
    spark,
    config.audit_table_name(),
    build_audit_record(
        step_name="quality_validation",
        batch_id=batch_id,
        status="SUCCESS",
        input_count=len(quality_rows),
        output_count=len(quality_rows),
        message="Quality checks completed",
        started_at=started_at,
        ended_at=utc_now_iso(),
    ),
)

display(spark.table(config.quality_table_name()).orderBy("checked_at"))
