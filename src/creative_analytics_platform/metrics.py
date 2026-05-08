from __future__ import annotations

from collections import defaultdict
from typing import Any

from .transforms import parse_iso_datetime


def _date_from_timestamp(value: str | None) -> str:
    return parse_iso_datetime(value).date().isoformat()


def _month_from_timestamp(value: str | None) -> str:
    dt = parse_iso_datetime(value)
    return f"{dt.year:04d}-{dt.month:02d}"


def build_daily_product_metrics(
    events: list[dict[str, Any]],
    subscriptions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    metrics_by_day: dict[str, dict[str, Any]] = {}
    paid_workspaces = {
        record["workspace_id"]
        for record in subscriptions
        if str(record.get("status", "")).lower() == "active" and int(record.get("monthly_recurring_revenue", 0) or 0) > 0
    }
    current_mrr = sum(
        int(record.get("monthly_recurring_revenue", 0) or 0)
        for record in subscriptions
        if str(record.get("status", "")).lower() == "active"
    )

    for event in events:
        metric_date = _date_from_timestamp(event.get("event_ts"))
        day_metrics = metrics_by_day.setdefault(
            metric_date,
            {
                "metric_date": metric_date,
                "active_users": set(),
                "active_workspaces": set(),
                "publish_events": 0,
            },
        )
        day_metrics["active_users"].add(event.get("user_id"))
        day_metrics["active_workspaces"].add(event.get("workspace_id"))
        if event.get("event_name") == "publish":
            day_metrics["publish_events"] += 1

    results: list[dict[str, Any]] = []
    for metric_date, payload in sorted(metrics_by_day.items()):
        results.append(
            {
                "metric_date": metric_date,
                "active_users": len(payload["active_users"]),
                "active_workspaces": len(payload["active_workspaces"]),
                "publish_events": payload["publish_events"],
                "paid_workspaces": len(paid_workspaces),
                "monthly_recurring_revenue": current_mrr,
            }
        )
    return results


def build_activation_funnel(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tracked_stages = ["signup", "create_project", "upload_asset", "generate_asset", "publish"]
    counts_by_day = defaultdict(lambda: {stage: set() for stage in tracked_stages})

    for event in events:
        event_name = event.get("event_name")
        if event_name not in tracked_stages:
            continue
        metric_date = _date_from_timestamp(event.get("event_ts"))
        counts_by_day[metric_date][event_name].add(event.get("workspace_id"))

    results: list[dict[str, Any]] = []
    for metric_date in sorted(counts_by_day):
        stage_counts = counts_by_day[metric_date]
        results.append(
            {
                "metric_date": metric_date,
                "signup_workspaces": len(stage_counts["signup"]),
                "created_project_workspaces": len(stage_counts["create_project"]),
                "uploaded_asset_workspaces": len(stage_counts["upload_asset"]),
                "generated_asset_workspaces": len(stage_counts["generate_asset"]),
                "published_workspaces": len(stage_counts["publish"]),
            }
        )
    return results


def build_feature_adoption(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = defaultdict(lambda: {"users": set(), "workspaces": set(), "event_count": 0})
    for event in events:
        metric_date = _date_from_timestamp(event.get("event_ts"))
        key = (metric_date, event.get("event_name"))
        grouped[key]["users"].add(event.get("user_id"))
        grouped[key]["workspaces"].add(event.get("workspace_id"))
        grouped[key]["event_count"] += 1

    results: list[dict[str, Any]] = []
    for (metric_date, event_name), payload in sorted(grouped.items()):
        results.append(
            {
                "metric_date": metric_date,
                "event_name": event_name,
                "unique_users": len(payload["users"]),
                "unique_workspaces": len(payload["workspaces"]),
                "event_count": payload["event_count"],
            }
        )
    return results


def build_workspace_retention(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    first_seen_by_workspace: dict[str, str] = {}
    active_months = defaultdict(set)
    for event in events:
        workspace_id = event.get("workspace_id")
        event_month = _month_from_timestamp(event.get("event_ts"))
        active_months[workspace_id].add(event_month)
        if workspace_id not in first_seen_by_workspace:
            first_seen_by_workspace[workspace_id] = event_month
        else:
            first_seen_by_workspace[workspace_id] = min(first_seen_by_workspace[workspace_id], event_month)

    grouped = defaultdict(lambda: {"cohort_size": set(), "retained": set()})
    for workspace_id, active_set in active_months.items():
        cohort_month = first_seen_by_workspace[workspace_id]
        for active_month in active_set:
            grouped[(cohort_month, active_month)]["cohort_size"].add(workspace_id)
            grouped[(cohort_month, active_month)]["retained"].add(workspace_id)

    results: list[dict[str, Any]] = []
    for (cohort_month, activity_month), payload in sorted(grouped.items()):
        cohort_size = len(payload["cohort_size"])
        retained = len(payload["retained"])
        results.append(
            {
                "cohort_month": cohort_month,
                "activity_month": activity_month,
                "retained_workspaces": retained,
                "cohort_size": cohort_size,
                "retention_rate": round(retained / cohort_size, 4) if cohort_size else 0.0,
            }
        )
    return results


def build_experiment_readout(
    events: list[dict[str, Any]],
    experiments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    events_by_user = defaultdict(list)
    for event in events:
        events_by_user[event.get("user_id")].append(event)

    grouped = defaultdict(lambda: {"assigned": 0, "generated": 0, "published": 0})
    for assignment in experiments:
        assigned_at = parse_iso_datetime(assignment.get("assigned_at"))
        user_events = [
            event
            for event in events_by_user.get(assignment.get("user_id"), [])
            if parse_iso_datetime(event.get("event_ts")) >= assigned_at
        ]
        key = (assignment.get("experiment_id"), assignment.get("experiment_name"), assignment.get("variant"))
        grouped[key]["assigned"] += 1
        if any(event.get("event_name") == "generate_asset" for event in user_events):
            grouped[key]["generated"] += 1
        if any(event.get("event_name") == "publish" for event in user_events):
            grouped[key]["published"] += 1

    results: list[dict[str, Any]] = []
    for (experiment_id, experiment_name, variant), payload in sorted(grouped.items()):
        assigned = payload["assigned"]
        published = payload["published"]
        results.append(
            {
                "experiment_id": experiment_id,
                "experiment_name": experiment_name,
                "variant": variant,
                "assigned_users": assigned,
                "generated_users": payload["generated"],
                "published_users": published,
                "publish_conversion_rate": round(published / assigned, 4) if assigned else 0.0,
            }
        )
    return results


def build_support_topic_trends(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = defaultdict(lambda: {"count": 0, "negative": 0, "confidence": 0.0})
    for record in records:
        feedback_date = _date_from_timestamp(record.get("created_at"))
        key = (feedback_date, record.get("topic", "unknown"))
        grouped[key]["count"] += 1
        grouped[key]["confidence"] += float(record.get("confidence", 0.0) or 0.0)
        if record.get("sentiment") == "negative":
            grouped[key]["negative"] += 1

    results: list[dict[str, Any]] = []
    for (feedback_date, topic), payload in sorted(grouped.items()):
        count = payload["count"]
        results.append(
            {
                "feedback_date": feedback_date,
                "topic": topic,
                "ticket_count": count,
                "negative_ticket_count": payload["negative"],
                "avg_confidence": round(payload["confidence"] / count, 4) if count else 0.0,
            }
        )
    return results

