from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from creative_analytics_platform.metrics import (
    build_activation_funnel,
    build_daily_product_metrics,
    build_experiment_readout,
    build_support_topic_trends,
)


class MetricBuilderTest(unittest.TestCase):
    def test_daily_metrics_and_activation(self) -> None:
        events = [
            {"event_ts": "2026-03-01T08:00:00Z", "user_id": "U001", "workspace_id": "W001", "event_name": "signup"},
            {"event_ts": "2026-03-01T08:10:00Z", "user_id": "U001", "workspace_id": "W001", "event_name": "create_project"},
            {"event_ts": "2026-03-01T08:20:00Z", "user_id": "U001", "workspace_id": "W001", "event_name": "publish"},
        ]
        subscriptions = [
            {"workspace_id": "W001", "status": "active", "monthly_recurring_revenue": "299"},
        ]
        daily = build_daily_product_metrics(events, subscriptions)
        funnel = build_activation_funnel(events)
        self.assertEqual(daily[0]["publish_events"], 1)
        self.assertEqual(daily[0]["paid_workspaces"], 1)
        self.assertEqual(funnel[0]["published_workspaces"], 1)

    def test_experiment_conversion_and_support_topics(self) -> None:
        events = [
            {"event_ts": "2026-03-01T08:30:00Z", "user_id": "U001", "workspace_id": "W001", "event_name": "generate_asset"},
            {"event_ts": "2026-03-01T08:45:00Z", "user_id": "U001", "workspace_id": "W001", "event_name": "publish"},
        ]
        experiments = [
            {
                "experiment_id": "EXP001",
                "experiment_name": "smart_generate_prompting",
                "variant": "control",
                "user_id": "U001",
                "assigned_at": "2026-03-01T08:00:00Z",
            }
        ]
        readout = build_experiment_readout(events, experiments)
        topics = build_support_topic_trends(
            [
                {"created_at": "2026-03-01T10:00:00Z", "topic": "billing", "sentiment": "negative", "confidence": 0.9},
                {"created_at": "2026-03-01T11:00:00Z", "topic": "billing", "sentiment": "neutral", "confidence": 0.8},
            ]
        )
        self.assertEqual(readout[0]["published_users"], 1)
        self.assertEqual(readout[0]["publish_conversion_rate"], 1.0)
        self.assertEqual(topics[0]["ticket_count"], 2)
        self.assertEqual(topics[0]["negative_ticket_count"], 1)


if __name__ == "__main__":
    unittest.main()
