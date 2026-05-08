from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from creative_analytics_platform.config import ProjectConfig
from creative_analytics_platform.contracts import load_all_contracts


class ConfigAndContractsTest(unittest.TestCase):
    def test_project_config_loads_and_builds_names(self) -> None:
        config = ProjectConfig.from_path(ROOT / "conf" / "project_config.yml")
        self.assertEqual(config.catalog, "main")
        self.assertEqual(config.schema_name("bronze"), "creative_saas_analytics_bronze")
        self.assertEqual(
            config.full_table_name("silver", "app_events"),
            "main.creative_saas_analytics_silver.silver_app_events",
        )
        self.assertEqual(
            config.full_table_name("gold", "gold_daily_product_metrics"),
            "main.creative_saas_analytics_gold.gold_daily_product_metrics",
        )

    def test_contracts_load_all_entities(self) -> None:
        contracts = load_all_contracts(ROOT / "conf" / "schemas")
        self.assertEqual(set(contracts), {"app_events", "users_workspaces", "subscriptions", "experiments", "support_feedback"})
        self.assertIn("event_name", contracts["app_events"].column_names)
        self.assertIn("email", contracts["users_workspaces"].pii_columns)


if __name__ == "__main__":
    unittest.main()
