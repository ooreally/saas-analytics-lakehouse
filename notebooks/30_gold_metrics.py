# Databricks notebook source
# MAGIC %md
# MAGIC # 30 Gold Metrics
# MAGIC
# MAGIC Builds the analytics-ready gold tables for daily product metrics, activation, adoption, retention, and experiments.

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
from creative_analytics_platform.runtime import append_audit_record, merge_into_delta

try:
    dbutils.widgets.text("batch_id", "2026-03-01")
    batch_id = dbutils.widgets.get("batch_id")
except NameError:
    batch_id = "2026-03-01"

config = ProjectConfig.from_path(repo_root / "conf" / "project_config.yml")

silver_events = config.full_table_name("silver", "app_events")
silver_subscriptions = config.full_table_name("silver", "subscriptions")
silver_experiments = config.full_table_name("silver", "experiments")

daily_metrics_sql = f"""
WITH daily_events AS (
  SELECT
    to_date(event_ts) AS metric_date,
    count(DISTINCT user_id) AS active_users,
    count(DISTINCT workspace_id) AS active_workspaces,
    sum(CASE WHEN event_name = 'publish' THEN 1 ELSE 0 END) AS publish_events
  FROM {silver_events}
  GROUP BY 1
),
subscription_snapshot AS (
  SELECT
    count(DISTINCT workspace_id) AS paid_workspaces,
    sum(monthly_recurring_revenue) AS monthly_recurring_revenue
  FROM {silver_subscriptions}
  WHERE status = 'active' AND monthly_recurring_revenue > 0
)
SELECT
  metric_date,
  active_users,
  active_workspaces,
  publish_events,
  paid_workspaces,
  monthly_recurring_revenue
FROM daily_events
CROSS JOIN subscription_snapshot
"""

activation_sql = f"""
SELECT
  to_date(event_ts) AS metric_date,
  count(DISTINCT CASE WHEN event_name = 'signup' THEN workspace_id END) AS signup_workspaces,
  count(DISTINCT CASE WHEN event_name = 'create_project' THEN workspace_id END) AS created_project_workspaces,
  count(DISTINCT CASE WHEN event_name = 'upload_asset' THEN workspace_id END) AS uploaded_asset_workspaces,
  count(DISTINCT CASE WHEN event_name = 'generate_asset' THEN workspace_id END) AS generated_asset_workspaces,
  count(DISTINCT CASE WHEN event_name = 'publish' THEN workspace_id END) AS published_workspaces
FROM {silver_events}
GROUP BY 1
"""

feature_adoption_sql = f"""
SELECT
  to_date(event_ts) AS metric_date,
  event_name,
  count(DISTINCT user_id) AS unique_users,
  count(DISTINCT workspace_id) AS unique_workspaces,
  count(*) AS event_count
FROM {silver_events}
GROUP BY 1, 2
"""

retention_sql = f"""
WITH activity AS (
  SELECT DISTINCT
    workspace_id,
    date_trunc('month', to_timestamp(event_ts)) AS activity_month
  FROM {silver_events}
),
cohorts AS (
  SELECT
    workspace_id,
    min(activity_month) AS cohort_month
  FROM activity
  GROUP BY 1
)
SELECT
  date_format(c.cohort_month, 'yyyy-MM') AS cohort_month,
  date_format(a.activity_month, 'yyyy-MM') AS activity_month,
  count(DISTINCT a.workspace_id) AS retained_workspaces,
  count(DISTINCT c.workspace_id) AS cohort_size,
  round(count(DISTINCT a.workspace_id) / count(DISTINCT c.workspace_id), 4) AS retention_rate
FROM activity a
JOIN cohorts c
  ON a.workspace_id = c.workspace_id
GROUP BY 1, 2
"""

experiment_sql = f"""
WITH post_assignment AS (
  SELECT
    x.experiment_id,
    x.experiment_name,
    x.variant,
    x.user_id,
    max(CASE WHEN e.event_name = 'generate_asset' AND to_timestamp(e.event_ts) >= to_timestamp(x.assigned_at) THEN 1 ELSE 0 END) AS generated_after_assignment,
    max(CASE WHEN e.event_name = 'publish' AND to_timestamp(e.event_ts) >= to_timestamp(x.assigned_at) THEN 1 ELSE 0 END) AS published_after_assignment
  FROM {silver_experiments} x
  LEFT JOIN {silver_events} e
    ON x.user_id = e.user_id
   AND x.workspace_id = e.workspace_id
  GROUP BY 1, 2, 3, 4
)
SELECT
  experiment_id,
  experiment_name,
  variant,
  count(*) AS assigned_users,
  sum(generated_after_assignment) AS generated_users,
  sum(published_after_assignment) AS published_users,
  round(sum(published_after_assignment) / count(*), 4) AS publish_conversion_rate
FROM post_assignment
GROUP BY 1, 2, 3
"""

metric_specs = [
    ("gold_daily_product_metrics", daily_metrics_sql, ["metric_date"]),
    ("gold_activation_funnel", activation_sql, ["metric_date"]),
    ("gold_feature_adoption", feature_adoption_sql, ["metric_date", "event_name"]),
    ("gold_workspace_retention", retention_sql, ["cohort_month", "activity_month"]),
    ("gold_experiment_readout", experiment_sql, ["experiment_id", "variant"]),
]

for table_name, query, merge_keys in metric_specs:
    started_at = utc_now_iso()
    dataframe = spark.sql(query)
    merge_into_delta(spark, config.full_table_name("gold", table_name), dataframe, merge_keys)
    append_audit_record(
        spark,
        config.audit_table_name(),
        build_audit_record(
            step_name=table_name,
            batch_id=batch_id,
            status="SUCCESS",
            input_count=0,
            output_count=dataframe.count(),
            message=f"Built {table_name}",
            started_at=started_at,
            ended_at=utc_now_iso(),
        ),
    )

display(spark.table(config.full_table_name("gold", "gold_daily_product_metrics")))
